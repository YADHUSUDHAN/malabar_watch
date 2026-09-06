# ==============================================================================
# Terraform Outputs - Malabar Watch AWS Infrastructure
# ==============================================================================

output "instance_id" {
  description = "The EC2 Instance ID"
  value       = aws_instance.malabar_agent.id
}

output "instance_state" {
  description = "Current lifecycle state of the instance"
  value       = aws_instance.malabar_agent.instance_state
}

output "aws_region" {
  description = "AWS deployment region"
  value       = var.aws_region
}

output "ssm_connect_command" {
  description = "Command to connect securely via AWS SSM without SSH keys or open ports"
  value       = "aws ssm start-session --target ${aws_instance.malabar_agent.id} --region ${var.aws_region}"
}

output "aws_console_session_url" {
  description = "One-click AWS Console browser terminal link"
  value       = "https://${var.aws_region}.console.aws.amazon.com/systems-manager/session-manager/${aws_instance.malabar_agent.id}?region=${var.aws_region}"
}

output "security_group_id" {
  description = "The zero-inbound security group ID"
  value       = aws_security_group.malabar_sg.id
}
