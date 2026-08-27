# -----------------------------------------------------------------------------
# S3 — RAG corpus / knowledge-base objects.
# Private, encrypted, versioned, with a lifecycle that keeps demo-scale
# storage effectively free (STANDARD_IA at 30d, expire at 90d).
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "corpus" {
  count = var.enable_aws ? 1 : 0

  bucket        = "${var.project}-corpus-${random_string.suffix.result}"
  force_destroy = true # demo posture: allow clean teardown

  tags = { Name = "${var.project}-corpus" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "corpus" {
  count = var.enable_aws ? 1 : 0

  bucket = aws_s3_bucket.corpus[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "corpus" {
  count = var.enable_aws ? 1 : 0

  bucket                  = aws_s3_bucket.corpus[0].id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "corpus" {
  count = var.enable_aws ? 1 : 0

  bucket = aws_s3_bucket.corpus[0].id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "corpus" {
  count = var.enable_aws ? 1 : 0

  bucket = aws_s3_bucket.corpus[0].id

  rule {
    id     = "archive-and-expire"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    expiration {
      days = 90
    }
  }
}
