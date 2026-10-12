from app.core.security import hash_password, verify_password

password = "MyPassword123!"

hashed_password = hash_password(password)

print("Hashed pwd:", hashed_password)
print("Correct pwd:", verify_password(password, hashed_password))
print("Wrong pwd:", verify_password("WrongPassword", hashed_password))
