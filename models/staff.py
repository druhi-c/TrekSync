from extensions import db


class StaffProfile(db.Model):
    __tablename__ = "staff_profiles"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        unique=True
    )

    phone = db.Column(db.String(15))

    experience = db.Column(db.Integer, default=0)

    emergency_contact = db.Column(db.String(15))

    bio = db.Column(db.Text)

    user = db.relationship(
        "User",
        back_populates="staff_profile"
    )

    def __repr__(self):
        return f"<StaffProfile User ID: {self.user_id}>"