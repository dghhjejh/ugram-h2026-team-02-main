






data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  selected_azs = slice(data.aws_availability_zones.available.names, 0, 2)
}

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
}

resource "aws_subnet" "public" {
  for_each = tomap({
    for index, cidr in var.public_subnet_cidrs : index => cidr
  })

  vpc_id                  = aws_vpc.main.id
  cidr_block              = each.value
  availability_zone       = local.selected_azs[tonumber(each.key)]
  map_public_ip_on_launch = true
}

resource "aws_subnet" "private" {
  for_each = tomap({
    for index, cidr in var.private_subnet_cidrs : index => cidr
  })

  vpc_id            = aws_vpc.main.id
  cidr_block        = each.value
  availability_zone = local.selected_azs[tonumber(each.key)]
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
}

resource "aws_route_table_association" "public" {
  for_each = aws_subnet.public

  subnet_id      = each.value.id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "backend" {
  name        = "${var.project}-${var.env}-backend"
  description = "Security group reserved for backend compute resources"
  vpc_id      = aws_vpc.main.id
}

resource "aws_security_group" "database" {
  name        = "${var.project}-${var.env}-database"
  description = "Allow PostgreSQL access from backend resources only"
  vpc_id      = aws_vpc.main.id
}

resource "aws_security_group_rule" "database_from_backend" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.database.id
  source_security_group_id = aws_security_group.backend.id
}

resource "aws_security_group_rule" "database_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  security_group_id = aws_security_group.database.id
  cidr_blocks       = ["0.0.0.0/0"]
}

resource "aws_security_group_rule" "backend_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  security_group_id = aws_security_group.backend.id
  cidr_blocks       = ["0.0.0.0/0"]
}

resource "aws_security_group_rule" "backend_http_ingress" {
  type              = "ingress"
  from_port         = 80
  to_port           = 80
  protocol          = "tcp"
  security_group_id = aws_security_group.backend.id
  cidr_blocks       = ["0.0.0.0/0"]
}
