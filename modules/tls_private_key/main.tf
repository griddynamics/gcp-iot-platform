resource "tls_private_key" "generating_key" {
  algorithm = var.algorithm
  rsa_bits  = var.rsa_bits
}

data "template_file" "private_key" {
    template = <<-EOF
    ${tls_private_key.generating_key.private_key_pem}
    EOF
}

resource "local_sensitive_file" "private_key" {
  depends_on = [data.template_file.private_key]
  content = data.template_file.private_key.rendered
  filename = "${var.path_module}/template/private_key.pem"
}
