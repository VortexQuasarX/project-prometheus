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
resource "aws_db_instance" "postgres" {
  count = var.enable_aws ? 1 : 0

  identifier              = "${var.project}-db"
  engine                  = "postgres"
  engine_version          = "15.13"
  instance_class          = "db.t4g.micro"
  allocated_storage       = 20
  max_allocated_storage   = 50
  storage_type            = "gp2"
  db_name                 = var.db_name
  username                = "prometheus_admin"
  password                = random_password.db_master[0].result
  db_subnet_group_name    = aws_db_subnet_group.aurora[0].name
  vpc_security_group_ids  = [aws_security_group.db[0].id]
  storage_encrypted       = true
  skip_final_snapshot     = true
  deletion_protection     = false
  backup_retention_period = var.backup_retention_days
  publicly_accessible     = false
  apply_immediately       = true

  tags = { Name = "${var.project}-db" }
}

resource "aws_db_subnet_group" "aurora" {
  count = var.enable_aws ? 1 : 0

  name       = "${var.project}-aurora-subnets"
  subnet_ids = [for subnet in aws_subnet.private : subnet.id]

  tags = { Name = "${var.project}-aurora-subnets" }
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
  description = "PostgreSQL master credentials (auto-rotated in production)."

  tags = { Name = "${var.project}-db-secret" }
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  count = var.enable_aws ? 1 : 0

  secret_id = aws_secretsmanager_secret.db_credentials[0].id
  secret_string = jsonencode({
    username = "prometheus_admin"
    password = random_password.db_master[0].result
    host     = aws_db_instance.postgres[0].address
    port     = 5432
    dbname   = var.db_name
  })
}
