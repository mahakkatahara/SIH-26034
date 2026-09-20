"""initial_schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-09-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # Define all ENUMs with checkfirst=True
    user_role = postgresql.ENUM('ADMIN', 'INSPECTOR', 'VIEWER', name='user_role')
    user_role.create(bind, checkfirst=True)

    violation_severity = postgresql.ENUM('HIGH', 'MEDIUM', 'LOW', 'INFO', name='violation_severity')
    violation_severity.create(bind, checkfirst=True)

    inspection_status = postgresql.ENUM(
        'DRAFT', 'IN_PROGRESS', 'ANALYSIS_PENDING', 'ANALYSIS_COMPLETE', 'COMPLETED', 'CANCELLED',
        name='inspection_status'
    )
    inspection_status.create(bind, checkfirst=True)

    compliance_status = postgresql.ENUM(
        'COMPLIANT', 'NON_COMPLIANT', 'WARNING', 'NEEDS_REVIEW', 'PENDING',
        name='compliance_status'
    )
    compliance_status.create(bind, checkfirst=True)

    pipeline_status = postgresql.ENUM(
        'NOT_STARTED', 'PREPROCESSING', 'OCR', 'EXTRACTION', 'RULE_CHECK', 'COMPLETED', 'FAILED', 'DEV_STUB',
        name='pipeline_status'
    )
    pipeline_status.create(bind, checkfirst=True)

    image_label = postgresql.ENUM('FRONT', 'BACK', 'SIDE', 'TOP', 'BOTTOM', 'OTHER', name='image_label')
    image_label.create(bind, checkfirst=True)

    processing_status = postgresql.ENUM('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'STUB', name='processing_status')
    processing_status.create(bind, checkfirst=True)

    violation_status = postgresql.ENUM('OPEN', 'ACKNOWLEDGED', 'RESOLVED', 'FALSE_POSITIVE', name='violation_status')
    violation_status.create(bind, checkfirst=True)

    report_type = postgresql.ENUM('PDF', 'DOCX', name='report_type')
    report_type.create(bind, checkfirst=True)

    report_status = postgresql.ENUM('PENDING', 'GENERATING', 'COMPLETED', 'FAILED', 'STUB', name='report_status')
    report_status.create(bind, checkfirst=True)

    # ─── users ────────────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('role', postgresql.ENUM('ADMIN', 'INSPECTOR', 'VIEWER', name='user_role', create_type=False), nullable=False),
        sa.Column('employee_id', sa.String(length=100), nullable=True),
        sa.Column('department', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # ─── products ─────────────────────────────────────────────────────────
    op.create_table(
        'products',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('category', sa.String(length=255), nullable=True),
        sa.Column('brand', sa.String(length=255), nullable=True),
        sa.Column('barcode', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('manufacturer_name', sa.String(length=500), nullable=True),
        sa.Column('manufacturer_address', sa.Text(), nullable=True),
        sa.Column('country_of_origin', sa.String(length=100), nullable=True),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_products_barcode'), 'products', ['barcode'], unique=False)
    op.create_index(op.f('ix_products_category'), 'products', ['category'], unique=False)

    # ─── rules ────────────────────────────────────────────────────────────
    # Baseline rules schema (before dee740111ad5 adds package_type & citation_verified)
    op.create_table(
        'rules',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('rule_id', sa.String(length=50), nullable=False),
        sa.Column('field', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=255), nullable=True),
        sa.Column('mandatory', sa.Boolean(), nullable=False),
        sa.Column('severity', postgresql.ENUM('HIGH', 'MEDIUM', 'LOW', 'INFO', name='violation_severity', create_type=False), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('validation_logic', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('legal_reference', sa.Text(), nullable=True),
        sa.Column('rule_version', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_rules_field'), 'rules', ['field'], unique=False)
    op.create_index(op.f('ix_rules_rule_id'), 'rules', ['rule_id'], unique=True)

    # ─── inspections ──────────────────────────────────────────────────────
    op.create_table(
        'inspections',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('inspection_number', sa.String(length=50), nullable=False),
        sa.Column('status', postgresql.ENUM('DRAFT', 'IN_PROGRESS', 'ANALYSIS_PENDING', 'ANALYSIS_COMPLETE', 'COMPLETED', 'CANCELLED', name='inspection_status', create_type=False), nullable=False),
        sa.Column('overall_compliance_status', postgresql.ENUM('COMPLIANT', 'NON_COMPLIANT', 'WARNING', 'NEEDS_REVIEW', 'PENDING', name='compliance_status', create_type=False), nullable=False),
        sa.Column('product_id', sa.UUID(), nullable=True),
        sa.Column('inspector_id', sa.UUID(), nullable=False),
        sa.Column('ai_pipeline_status', postgresql.ENUM('NOT_STARTED', 'PREPROCESSING', 'OCR', 'EXTRACTION', 'RULE_CHECK', 'COMPLETED', 'FAILED', 'DEV_STUB', name='pipeline_status', create_type=False), nullable=False),
        sa.Column('ai_confidence_score', sa.Float(), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('location', sa.String(length=500), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['inspector_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_inspections_inspection_number'), 'inspections', ['inspection_number'], unique=True)

    # ─── inspection_images ────────────────────────────────────────────────
    op.create_table(
        'inspection_images',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('inspection_id', sa.UUID(), nullable=False),
        sa.Column('image_path', sa.String(length=1000), nullable=False),
        sa.Column('label', postgresql.ENUM('FRONT', 'BACK', 'SIDE', 'TOP', 'BOTTOM', 'OTHER', name='image_label', create_type=False), nullable=False),
        sa.Column('original_filename', sa.String(length=500), nullable=True),
        sa.Column('file_size', sa.BigInteger(), nullable=True),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('processing_status', postgresql.ENUM('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'STUB', name='processing_status', create_type=False), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['inspection_id'], ['inspections.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # ─── declarations ─────────────────────────────────────────────────────
    op.create_table(
        'declarations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('inspection_id', sa.UUID(), nullable=False),
        sa.Column('image_id', sa.UUID(), nullable=True),
        sa.Column('field_name', sa.String(length=100), nullable=False),
        sa.Column('field_value', sa.Text(), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('bounding_box', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('extraction_method', sa.String(length=100), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False),
        sa.Column('verified_by_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['image_id'], ['inspection_images.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['inspection_id'], ['inspections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['verified_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_declarations_field_name'), 'declarations', ['field_name'], unique=False)

    # ─── ocr_regions ──────────────────────────────────────────────────────
    op.create_table(
        'ocr_regions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('inspection_id', sa.UUID(), nullable=False),
        sa.Column('image_id', sa.UUID(), nullable=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('bounding_box', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('language', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['image_id'], ['inspection_images.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['inspection_id'], ['inspections.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ocr_regions_image_id'), 'ocr_regions', ['image_id'], unique=False)
    op.create_index(op.f('ix_ocr_regions_inspection_id'), 'ocr_regions', ['inspection_id'], unique=False)

    # ─── violations ───────────────────────────────────────────────────────
    op.create_table(
        'violations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('inspection_id', sa.UUID(), nullable=False),
        sa.Column('rule_id', sa.UUID(), nullable=True),
        sa.Column('declaration_id', sa.UUID(), nullable=True),
        sa.Column('severity', postgresql.ENUM('HIGH', 'MEDIUM', 'LOW', 'INFO', name='violation_severity', create_type=False), nullable=False),
        sa.Column('status', postgresql.ENUM('OPEN', 'ACKNOWLEDGED', 'RESOLVED', 'FALSE_POSITIVE', name='violation_status', create_type=False), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('legal_reference', sa.Text(), nullable=True),
        sa.Column('evidence_region', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['declaration_id'], ['declarations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['inspection_id'], ['inspections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resolved_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['rule_id'], ['rules.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    # ─── reports ──────────────────────────────────────────────────────────
    op.create_table(
        'reports',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('inspection_id', sa.UUID(), nullable=False),
        sa.Column('report_type', postgresql.ENUM('PDF', 'DOCX', name='report_type', create_type=False), nullable=False),
        sa.Column('file_path', sa.String(length=1000), nullable=True),
        sa.Column('generation_status', postgresql.ENUM('PENDING', 'GENERATING', 'COMPLETED', 'FAILED', 'STUB', name='report_status', create_type=False), nullable=False),
        sa.Column('generated_by_id', sa.UUID(), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['generated_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['inspection_id'], ['inspections.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('reports')
    op.drop_table('violations')
    op.drop_table('ocr_regions')
    op.drop_table('declarations')
    op.drop_table('inspection_images')
    op.drop_table('inspections')
    op.drop_table('rules')
    op.drop_table('products')
    op.drop_table('users')

    bind = op.get_bind()
    for enum_name in [
        'report_status', 'report_type', 'violation_status', 'violation_severity',
        'pipeline_status', 'processing_status', 'image_label', 'compliance_status',
        'inspection_status', 'user_role'
    ]:
        sa.Enum(name=enum_name).drop(bind, checkfirst=True)
