from werkzeug.security import generate_password_hash
from app import app, db, User, Customer


def ensure_admin_user(username: str, email: str, password: str) -> None:
	with app.app_context():
		# Ensure tables exist
		db.create_all()

		existing = db.session.query(User).filter(
			(User.username == username) | (User.email == email)
		).first()
		if existing:
			# Ensure existing user has admin role and reset password
			existing.role = "admin"
			existing.password_hash = generate_password_hash(password)
			if not existing.full_name:
				existing.full_name = "Admin User"
			if not existing.phone:
				existing.phone = "0000000000"
			db.session.commit()
			print(
				f"Updated admin user: username='{existing.username}', email='{existing.email}', password reset."
			)
			return

		user = User(
			username=username,
			email=email,
			password_hash=generate_password_hash(password),
			full_name="Admin User",
			phone="0000000000",
			role="admin",
		)
		db.session.add(user)
		db.session.flush()

		# Create a basic Customer profile to satisfy relationships used in templates
		customer = Customer(
			user_id=user.id,
			customer_id=f"CUST{user.id:05d}",
		)
		db.session.add(customer)
		db.session.commit()
		print(
			f"Created admin user: username='{username}', email='{email}', password='{password}'"
		)


if __name__ == "__main__":
	# Default credentials; change as needed
	ensure_admin_user(username="admin", email="admin@example.com", password="admin123")


