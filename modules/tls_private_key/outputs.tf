output "public_key" {
  value = tls_private_key.generating_key.public_key_pem
}

output "private_key" {
  value = tls_private_key.generating_key.private_key_pem
}
