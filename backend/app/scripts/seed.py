"""
Seed script — creates default users and loads rules from rules.json into the database.
Run: python -m app.scripts.seed
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy import select
from app.database.session import AsyncSessionFactory
from app.models.user import User
from app.models.rule import Rule
from app.core.security import hash_password


DEFAULT_USERS = [
    {
        "email": "admin@legalmetrology.gov.in",
        "password": "Admin@123",
        "full_name": "System Administrator",
        "role": "ADMIN",
        "employee_id": "ADMIN-001",
        "department": "Legal Metrology Division",
    },
    {
        "email": "inspector@legalmetrology.gov.in",
        "password": "Inspector@123",
        "full_name": "Field Inspector",
        "role": "INSPECTOR",
        "employee_id": "INS-001",
        "department": "Enforcement Wing",
    },
    {
        "email": "viewer@legalmetrology.gov.in",
        "password": "Viewer@123",
        "full_name": "Report Viewer",
        "role": "VIEWER",
        "employee_id": "VIW-001",
        "department": "Compliance Monitoring",
    },
]


async def seed():
    async with AsyncSessionFactory() as session:
        # ── Seed Users ────────────────────────────────────────────────────
        print("Seeding default users...")
        for user_data in DEFAULT_USERS:
            result = await session.execute(
                select(User).where(User.email == user_data["email"])
            )
            user = result.scalar_one_or_none()
            if user is None:
                user = User(
                    email=user_data["email"],
                    hashed_password=hash_password(user_data["password"]),
                    full_name=user_data["full_name"],
                    role=user_data["role"],
                    employee_id=user_data["employee_id"],
                    department=user_data["department"],
                )
                session.add(user)
                print(f"  Created user: {user_data['email']} ({user_data['role']})")
            else:
                user.full_name = user_data["full_name"]
                user.role = user_data["role"]
                user.employee_id = user_data["employee_id"]
                user.department = user_data["department"]
                print(f"  User already exists (synced): {user_data['email']}")

        # ── Seed Rules ────────────────────────────────────────────────────
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "rule-engine", "rules", "rules.json"),
            "/rule-engine/rules/rules.json",
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "rule-engine", "rules", "rules.json")),
        ]
        rules_path = next((p for p in possible_paths if os.path.exists(p)), None)
        if rules_path and os.path.exists(rules_path):
            print(f"Seeding compliance rules from {rules_path}...")
            with open(rules_path) as f:
                rules_data = json.load(f)

            for rule_data in rules_data:
                result = await session.execute(
                    select(Rule).where(Rule.rule_id == rule_data["rule_id"])
                )
                rule = result.scalar_one_or_none()
                if rule is None:
                    rule = Rule(
                        rule_id=rule_data["rule_id"],
                        field=rule_data["field"],
                        category=rule_data.get("category"),
                        mandatory=rule_data.get("mandatory", True),
                        severity=rule_data.get("severity", "HIGH"),
                        description=rule_data["description"],
                        validation_logic=rule_data.get("validation_logic"),
                        legal_reference=rule_data.get("legal_reference"),
                        rule_version=rule_data.get("rule_version", "1.0"),
                        package_type=rule_data.get("package_type", "retail"),
                        citation_verified=rule_data.get("citation_verified", False),
                    )
                    session.add(rule)
                    print(f"  Created rule: {rule_data['rule_id']}")
                else:
                    rule.field = rule_data["field"]
                    rule.category = rule_data.get("category")
                    rule.mandatory = rule_data.get("mandatory", True)
                    rule.severity = rule_data.get("severity", "HIGH")
                    rule.description = rule_data["description"]
                    rule.validation_logic = rule_data.get("validation_logic")
                    rule.legal_reference = rule_data.get("legal_reference")
                    rule.rule_version = rule_data.get("rule_version", "1.0")
                    rule.package_type = rule_data.get("package_type", "retail")
                    rule.citation_verified = rule_data.get("citation_verified", False)
                    print(f"  Updated rule: {rule_data['rule_id']}")
        else:
            print(f"  Rules file not found at {rules_path}, skipping rule seeding")

        await session.commit()
    print("Seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed())
