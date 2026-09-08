# -----------------------------------------------------------------------------
# VPC — private subnets only. No NAT by default (COST: NAT ≈ $33/mo ≈ 17% of
# the $197 credit); AWS access goes through VPC endpoints instead.
# -----------------------------------------------------------------------------
resource "aws_vpc" "main" {
  count = var.enable_aws ? 1 : 0

  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = "${var.project}-vpc" }
}

resource "aws_subnet" "private" {
  for_each = var.enable_aws ? toset(var.private_subnet_cidrs) : toset([])

  vpc_id            = aws_vpc.main[0].id
  cidr_block        = each.value
  availability_zone = "${var.aws_region}${each.key == element(var.private_subnet_cidrs, 0) ? "a" : "b"}"

  tags = { Name = "${var.project}-private-${each.key}" }
}

# API -> Aurora security group pair (least privilege: DB only from the API SG).
resource "aws_security_group" "api" {
  count = var.enable_aws ? 1 : 0

  name   = "${var.project}-api-sg"
  vpc_id = aws_vpc.main[0].id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project}-api-sg" }
}

resource "aws_security_group" "db" {
  count = var.enable_aws ? 1 : 0

  name   = "${var.project}-db-sg"
  vpc_id = aws_vpc.main[0].id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.api[0].id]
  }

  tags = { Name = "${var.project}-db-sg" }
}

# Free S3 gateway endpoint; interface endpoints only where needed.
resource "aws_vpc_endpoint" "s3" {
  count = var.enable_aws ? 1 : 0

  vpc_id            = aws_vpc.main[0].id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_vpc.main[0].default_route_table_id]

  tags = { Name = "${var.project}-s3-endpoint" }
}

resource "aws_vpc_endpoint" "secretsmanager" {
  count = var.enable_aws && var.enable_vpc_endpoints ? 1 : 0

  vpc_id              = aws_vpc.main[0].id
  service_name        = "com.amazonaws.${var.aws_region}.secretsmanager"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [for subnet in aws_subnet.private : subnet.id]
  security_group_ids  = [aws_security_group.api[0].id]
  private_dns_enabled = true

  tags = { Name = "${var.project}-secretsmanager-endpoint" }
}

resource "aws_vpc_endpoint" "bedrock_runtime" {
  count = var.enable_aws && var.enable_vpc_endpoints ? 1 : 0

  vpc_id              = aws_vpc.main[0].id
  service_name        = "com.amazonaws.${var.aws_region}.bedrock-runtime"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [for subnet in aws_subnet.private : subnet.id]
  security_group_ids  = [aws_security_group.api[0].id]
  private_dns_enabled = true

  tags = { Name = "${var.project}-bedrock-endpoint" }
}
