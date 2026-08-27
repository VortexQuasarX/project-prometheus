# -----------------------------------------------------------------------------
# Aurora Serverless v2 with pgvector.
#
# COST NOTES (read before applying):
# - Serverless v2 CANNOT scale to zero (0.5 ACU floor ≈ $43/mo at list).
#   Stop the cluster between demo windows (`aws rds stop-db-cluster`) — ACU
#   billing halts; storage (~$0.10/GB/mo) continues.
# - Serverless v2 uses engine_mode "provisioned" + serverlessv2_scaling
#   configuration (v1 "serverless" mode is a different, retired feature).
# - pgvector: `CREATE EXTENSION IF NOT EXISTS vector;` (SQL name is `vector`),
#   Aurora PostgreSQL 15.4+ required.
# - skip_final_snapshot=true is demo-only convenience; production must take a
#   final snapshot.
# -----------------------------------------------------------------------------
resource "aws_rds_cluster_parameter_group" "aurora" {
  count = var.enable_aws ? 1 : 0

  family = "aurora-postgresql15"
  name   = "${var.project}-aurora-pg"

  parameter {
    name  = "shared_preload_libraries"
    value = "vector"
  }

  tags = { Name = "${var.project}-aurora-pg" }
}

resource "aws_rds_cluster" "aurora" {
  count = var.enable_aws ? 1 : 0

  cluster_identifier              = "${var.project}-aurora"
  engine                          = "aurora-postgresql"
  engine_version                  = "15.7"
  database_name                   = var.db_name
  master_username                 = "prometheus_admin"
  master_password                 = random_password.db_master[0].result
  storage_encrypted               = true
  backup_retention_period         = var.backup_retention_days
  db_cluster_parameter_group_name = aws_rds_cluster_parameter_group.aurora[0].name
  db_subnet_group_name            = aws_db_subnet_group.aurora[0].name
  vpc_security_group_ids          = [aws_security_group.db[0].id]

  serverlessv2_scaling_configuration {
    min_capacity = var.aurora_min_acus
    max_capacity = var.aurora_max_acus
  }

  skip_final_snapshot   = true # demo posture; flip to false + identifier in prod
  deletion_protection   = false
  apply_immediately     = true

  tags = { Name = "${var.project}-aurora" }
}

resource "aws_db_subnet_group" "aurora" {
  count = var.enable_aws ? 1 : 0

  name       = "${var.project}-aurora-subnets"
  subnet_ids = [for subnet in aws_subnet.private : subnet.id]

  tags = { Name = "${var.project}-aurora-subnets" }
}

# Single db.serverless instance — no replicas (replicas add constant ACU cost).
resource "aws_rds_cluster_instance" "aurora" {
  count = var.enable_aws ? 1 : 0

  identifier         = "${var.project}-aurora-1"
  cluster_identifier = aws_rds_cluster.aurora[0].id
  instance_class     = "db.serverless"
  engine             = "aurora-postgresql"
  engine_version     = "15.7"

  tags = { Name = "${var.project}-aurora-1" }
}

resource "random_password" "db_master" {
  count = var.enable_aws ? 1 : 0

  length  = 24
  special = false
}

# Credentials live in Secrets Manager — never in tfvars or code.
resource "aws_secretsmanager_secret" "db_credentials" {
  count = var.enable_aws ? 1 : 0

  name        = "${var.project}/db/credentials"
  description = "Aurora master credentials (auto-rotated in production)."

  tags = { Name = "${var.project}-db-secret" }
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  count = var.enable_aws ? 1 : 0

  secret_id = aws_secretsmanager_secret.db_credentials[0].id
  secret_string = jsonencode({
    username = "prometheus_admin"
    password = random_password.db_master[0].result
    host     = aws_rds_cluster.aurora[0].endpoint
    dbname   = var.db_name
  })
}
