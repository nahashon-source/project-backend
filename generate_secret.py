import secrets

# Generate a secure random 16-byte (128-bit) secret key in hexadecimal format
secret_key = secrets.token_hex(16)  # 16 bytes = 128 bits
print(secret_key)
