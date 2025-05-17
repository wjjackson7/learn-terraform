provider "aws" {
  region = var.aws_region
}

resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}
data "aws_availability_zones" "available" {}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]  # picks a working AZ
  map_public_ip_on_launch = true
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
}

resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
}

resource "aws_route_table_association" "public_assoc" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public_rt.id
}

resource "aws_security_group" "web_sg" {
  name        = "web-sg"
  vpc_id      = aws_vpc.main.id
  description = "Allow HTTP, HTTPS, and SSH"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# IAM role for EC2 instance
resource "aws_iam_role" "ec2_role" {
  name = "ec2_instance_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

# IAM policy for EC2 instance
resource "aws_iam_role_policy" "ec2_policy" {
  name = "ec2_instance_policy"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:StopInstances",
          "ec2:DescribeInstances"
        ]
        Resource = "*"
      }
    ]
  })
}

# IAM instance profile
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "ec2_instance_profile"
  role = aws_iam_role.ec2_role.name
}

#aws ec2 instance definition
resource "aws_instance" "app" {
  ami                         = "ami-075686beab831bb7f"
  instance_type               = "t2.micro"
  subnet_id                   = aws_subnet.public.id
  key_name                    = var.key_pair
  vpc_security_group_ids      = [aws_security_group.web_sg.id]
  user_data                   = templatefile("setup.py", {
    aws_region = var.aws_region,
    app_repo   = var.app_repo,
    app_path   = var.app_path
  })
  associate_public_ip_address = true
  iam_instance_profile        = aws_iam_instance_profile.ec2_profile.name

  tags = {
    Name = "PythonApp"
  }

  # 🔽 Copy the local credentials folder to EC2
  provisioner "file" {
    source      = "${path.module}/../credentials"
    destination = "/home/ubuntu/credentials"

    connection {
      type        = "ssh"
      user        = "ubuntu"
      private_key = file("${path.module}/../credentials/terraform.pem")
      host        = self.public_ip
    }
  }

  # 🔽 Move it to /opt/app and ensure permissions
  provisioner "remote-exec" {
    inline = [
      "sudo mv /home/ubuntu/credentials /opt/app/",
      "sudo chown -R ubuntu:ubuntu /opt/app/credentials"
    ]

    connection {
      type        = "ssh"
      user        = "ubuntu"
      private_key = file("${path.module}/../credentials/terraform.pem")
      host        = self.public_ip
    }
  }

}

# state to track if my ec2 instance is running
resource "aws_ec2_instance_state" "app" {
  instance_id = aws_instance.app.id
  state       = var.instance_state
}

# IAM role for Lambda to manage EC2
resource "aws_iam_role" "lambda_ec2_role" {
  name = "lambda_ec2_management_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM policy for EC2 management
resource "aws_iam_role_policy" "lambda_ec2_policy" {
  name = "lambda_ec2_management_policy"
  role = aws_iam_role.lambda_ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:StartInstances",
          "ec2:DescribeInstances"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# Lambda function to start the instance
resource "aws_lambda_function" "start_instance" {
  filename         = "lambda/start_instance.zip"
  function_name    = "start_ec2_instance"
  role            = aws_iam_role.lambda_ec2_role.arn
  handler         = "start_instance.lambda_handler"
  runtime         = "python3.9"
  timeout         = 300

  environment {
    variables = {
      INSTANCE_ID = aws_instance.app.id
    }
  }
}

# CloudWatch Event Rule to start instance (e.g., every Monday at 9 AM UTC)
resource "aws_cloudwatch_event_rule" "start_instance" {
  name                = "start_ec2_instance"
  description         = "Start EC2 instance on schedule"
  schedule_expression = "cron(0 9 ? * MON *)"  # Every Monday at 9 AM UTC
}

# CloudWatch Event Target for starting instance
resource "aws_cloudwatch_event_target" "start_instance" {
  rule      = aws_cloudwatch_event_rule.start_instance.name
  target_id = "StartInstance"
  arn       = aws_lambda_function.start_instance.arn
}

# Lambda permission for CloudWatch Events to invoke start function
resource "aws_lambda_permission" "allow_cloudwatch_start" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.start_instance.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.start_instance.arn
}
