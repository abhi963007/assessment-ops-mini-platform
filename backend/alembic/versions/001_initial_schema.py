"""Initial schema - students, tests, attempts, scores, flags

Revision ID: 001
Revises: None
Create Date: 2026-02-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Students table
    op.create_table(
        'students',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('full_name', sa.Text(), nullable=False),
        sa.Column('email', sa.Text(), nullable=True),
        sa.Column('phone', sa.Text(), nullable=True),
        sa.Column('normalized_email', sa.Text(), nullable=True),
        sa.Column('normalized_phone', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_students_normalized_email', 'students', ['normalized_email'])
    op.create_index('ix_students_normalized_phone', 'students', ['normalized_phone'])

    # Tests table
    op.create_table(
        'tests',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.Text(), nullable=False, unique=True),
        sa.Column('max_marks', sa.Integer(), nullable=False),
        sa.Column('negative_marking', JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # Create enum type via raw SQL to avoid SQLAlchemy auto-creation conflicts
    op.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'attempt_status') THEN CREATE TYPE attempt_status AS ENUM ('INGESTED', 'DEDUPED', 'SCORED', 'FLAGGED'); END IF; END $$")

    # Attempts table
    op.create_table(
        'attempts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('student_id', UUID(as_uuid=True), sa.ForeignKey('students.id'), nullable=False),
        sa.Column('test_id', UUID(as_uuid=True), sa.ForeignKey('tests.id'), nullable=False),
        sa.Column('source_event_id', sa.Text(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('answers', JSONB(), nullable=False, server_default='{}'),
        sa.Column('raw_payload', JSONB(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False, server_default='INGESTED'),
        sa.Column('duplicate_of_attempt_id', UUID(as_uuid=True), sa.ForeignKey('attempts.id'), nullable=True),
    )
    # Convert status column from text to enum: drop default, alter type, re-add default
    op.execute("ALTER TABLE attempts ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE attempts ALTER COLUMN status TYPE attempt_status USING status::attempt_status")
    op.execute("ALTER TABLE attempts ALTER COLUMN status SET DEFAULT 'INGESTED'")
    op.create_index('ix_attempts_student_test', 'attempts', ['student_id', 'test_id'])
    op.create_index('ix_attempts_status', 'attempts', ['status'])
    op.create_index('ix_attempts_started_at', 'attempts', ['started_at'])

    # Attempt scores table
    op.create_table(
        'attempt_scores',
        sa.Column('attempt_id', UUID(as_uuid=True), sa.ForeignKey('attempts.id'), primary_key=True),
        sa.Column('correct', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('wrong', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('skipped', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('accuracy', sa.Numeric(7, 2), nullable=False, server_default='0'),
        sa.Column('net_correct', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('score', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('computed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('explanation', JSONB(), nullable=True),
    )

    # Flags table
    op.create_table(
        'flags',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('attempt_id', UUID(as_uuid=True), sa.ForeignKey('attempts.id'), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('flags')
    op.drop_table('attempt_scores')
    op.drop_table('attempts')
    op.drop_table('tests')
    op.drop_table('students')
    op.execute('DROP TYPE IF EXISTS attempt_status')
