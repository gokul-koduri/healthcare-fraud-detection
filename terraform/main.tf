# Terraform configuration for Healthcare Fraud Detection AWS Infrastructure

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
  }
  
  backend "s3" {
    bucket         = "healthcare-fraud-terraform-state"
    key            = "infrastructure/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "healthcare-fraud-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "healthcare-fraud-detection"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# VPC Module
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.project_name}-${var.environment}-vpc"
  cidr = var.vpc_cidr

  azs             = var.availability_zones
  private_subnets = var.private_subnet_cidrs
  public_subnets  = var.public_subnet_cidrs

  enable_nat_gateway   = true
  single_nat_gateway   = var.environment == "dev" ? true : false
  enable_dns_hostnames = true
  enable_dns_support   = true

  # Database subnets
  database_subnets = var.database_subnet_cidrs

  # Tags
  tags = {
    Environment = var.environment
  }
}

# EKS Cluster
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = "${var.project_name}-${var.environment}-cluster"
  cluster_version = "1.28"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  # Cluster addons
  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent = true
    }
    aws-ebs-csi-driver = {
      most_recent = true
    }
  }

  # EKS managed node groups
  eks_managed_node_groups = {
    main = {
      name = "${var.project_name}-node-group"

      instance_types = ["m5.xlarge", "m5.2xlarge"]
      capacity_type  = "ON_DEMAND"

      min_size     = 3
      max_size     = 10
      desired_size = 3

      disk_size = 100

      # IAM role
      create_iam_role = true
      iam_role_name   = "${var.project_name}-node-role"

      # Security groups
      create_security_group = true

      # Tags
      tags = {
        Environment = var.environment
      }
    }

    spot = {
      name = "${var.project_name}-spot-node-group"

      instance_types = ["m5.xlarge", "m5.2xlarge", "c5.xlarge"]
      capacity_type  = "SPOT"

      min_size     = 0
      max_size     = 5
      desired_size = 1

      disk_size = 100

      # Spot instance settings
      spot_instance_pools = 3

      tags = {
        Environment = var.environment
        Type        = "spot"
      }
    }
  }

  # Cluster security group
  cluster_security_group_additional_rules = {
    ingress_nodes_ephemeral_ports_tcp = {
      description                = "Nodes on ephemeral ports"
      protocol                   = "tcp"
      from_port                  = 1025
      to_port                    = 65535
      type                       = "ingress"
      source_node_security_group = true
    }
  }

  # OIDC provider
  enable_irsa = true

  tags = {
    Environment = var.environment
  }
}

# S3 Buckets
module "s3_buckets" {
  source = "./modules/s3"

  project_name = var.project_name
  environment  = var.environment

  buckets = {
    claims-data = {
      versioning = true
      lifecycle_rules = [
        {
          id      = "archive-old-data"
          enabled = true
          transition = {
            days          = 90
            storage_class = "GLACIER"
          }
        }
      ]
    }
    
    model-artifacts = {
      versioning = true
      lifecycle_rules = [
        {
          id      = "delete-old-models"
          enabled = true
          expiration = {
            days = 365
          }
        }
      ]
    }
    
    mlflow-artifacts = {
      versioning = true
    }
    
    dbt-artifacts = {
      versioning = false
    }
  }
}

# RDS for Snowflake/MLflow
module "rds" {
  source = "./modules/rds"

  project_name = var.project_name
  environment  = var.environment
  
  vpc_id      = module.vpc.vpc_id
  subnet_ids  = module.vpc.database_subnets
  
  # MLflow database
  databases = {
    mlflow = {
      engine         = "postgres"
      engine_version = "15.3"
      instance_class = "db.t3.medium"
      
      allocated_storage     = 20
      max_allocated_storage = 100
      
      db_name  = "mlflow"
      username = "mlflow"
      password = var.mlflow_db_password
      
      multi_az               = false
      storage_encrypted      = true
      backup_retention_period = 7
      
      tags = {
        Purpose = "MLflow"
      }
    }
  }
}

# ElastiCache Redis
module "elasticache" {
  source = "./modules/elasticache"

  project_name = var.project_name
  environment  = var.environment
  
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.database_subnets
  
  # Redis cluster
  redis = {
    node_type            = "cache.t3.medium"
    num_cache_nodes      = 1
    engine_version       = "7.0"
    port                 = 6379
    parameter_group_name = "default.redis7"
    
    at_rest_encryption_enabled = true
    transit_encryption_enabled  = true
    
    tags = {
      Purpose = "Caching"
    }
  }
}

# Lambda function
module "lambda" {
  source = "./modules/lambda"

  project_name = var.project_name
  environment  = var.environment

  # Claims processor Lambda
  functions = {
    claims_processor = {
      runtime          = "python3.11"
      handler          = "lambda_handler.lambda_handler"
      source_path      = "${path.module}/../lambda"
      timeout          = 300
      memory_size      = 512
      reserved_concurrent_executions = 10
      
      environment_variables = {
        CONFIG_PATH = "config/config.yaml"
        MODEL_PATH  = "models/ensemble_model_latest"
        LOG_LEVEL   = "INFO"
      }
      
      secrets = {
        OPENAI_API_KEY = aws_secretsmanager_secret.openai_api_key.arn
        SNOWFLAKE_CREDENTIALS = aws_secretsmanager_secret.snowflake_credentials.arn
        AWS_CREDENTIALS = aws_secretsmanager_secret.aws_credentials.arn
      }
      
      # S3 trigger
      s3_triggers = {
        claims_data = {
          bucket = module.s3_buckets.bucket_names["claims-data"]
          events = ["s3:ObjectCreated:*"]
          filter_prefix = "raw/"
        }
      }
      
      # CloudWatch logs
      enable_cloudwatch_logs = true
      log_retention_days     = 7
      
      # Dead letter queue
      dead_letter_queue_enabled = true
      
      tags = {
        Purpose = "Claims Processing"
      }
    }
  }
}

# Secrets Manager
resource "aws_secretsmanager_secret" "openai_api_key" {
  name = "${var.project_name}/${var.environment}/openai-api-key"
  description = "OpenAI API key for GenAI audit assistant"
}

resource "aws_secretsmanager_secret" "snowflake_credentials" {
  name = "${var.project_name}/${var.environment}/snowflake-credentials"
  description = "Snowflake database credentials"
}

resource "aws_secretsmanager_secret" "aws_credentials" {
  name = "${var.project_name}/${var.environment}/aws-credentials"
  description = "AWS credentials for cross-account access"
}

# CloudWatch Alarms
module "cloudwatch_alarms" {
  source = "./modules/cloudwatch"

  project_name = var.project_name
  environment  = var.environment

  # API alarms
  api_alarms = {
    high_error_rate = {
      metric_name        = "4xxError"
      namespace          = "AWS/ApplicationELB"
      statistic          = "Sum"
      period             = 300
      evaluation_periods = 1
      threshold          = 50
      comparison_operator = "GreaterThanOrEqualToThreshold"
      alarm_description   = "Alert when API error rate is high"
    }
    
    high_latency = {
      metric_name        = "TargetResponseTime"
      namespace          = "AWS/ApplicationELB"
      statistic          = "Average"
      period             = 300
      evaluation_periods = 2
      threshold          = 1
      comparison_operator = "GreaterThanOrEqualToThreshold"
      alarm_description   = "Alert when API latency is high"
    }
  }
  
  # Lambda alarms
  lambda_alarms = {
    high_error_rate = {
      metric_name        = "Errors"
      namespace          = "AWS/Lambda"
      statistic          = "Sum"
      period             = 60
      evaluation_periods = 3
      threshold          = 5
      comparison_operator = "GreaterThanOrEqualToThreshold"
      alarm_description   = "Alert when Lambda error rate is high"
    }
    
    throttles = {
      metric_name        = "Throttles"
      namespace          = "AWS/Lambda"
      statistic          = "Sum"
      period             = 300
      evaluation_periods = 1
      threshold          = 10
      comparison_operator = "GreaterThanOrEqualToThreshold"
      alarm_description   = "Alert when Lambda is being throttled"
    }
  }
}

# Outputs
output "vpc_id" {
  value = module.vpc.vpc_id
}

output "eks_cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "s3_bucket_names" {
  value = module.s3_buckets.bucket_names
}

output "lambda_function_names" {
  value = module.lambda.function_names
}

output "rds_endpoint" {
  value = module.rds.endpoints
}

output "elasticache_endpoint" {
  value = module.elasticache.endpoints
}
