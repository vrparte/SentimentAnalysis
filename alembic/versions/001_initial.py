"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Directors
    op.create_table(
        'directors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('aliases', sa.JSON(), nullable=True),
        sa.Column('context_terms', sa.JSON(), nullable=True),
        sa.Column('negative_terms', sa.JSON(), nullable=True),
        sa.Column('known_entities', sa.JSON(), nullable=True),
        sa.Column('provider_gdelt_enabled', sa.Boolean(), nullable=True),
        sa.Column('provider_bing_enabled', sa.Boolean(), nullable=True),
        sa.Column('provider_serpapi_enabled', sa.Boolean(), nullable=True),
        sa.Column('provider_rss_enabled', sa.Boolean(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_directors_id'), 'directors', ['id'], unique=False)
    op.create_index(op.f('ix_directors_full_name'), 'directors', ['full_name'], unique=False)

    # Articles
    op.create_table(
        'articles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(length=2048), nullable=False),
        sa.Column('canonical_url', sa.String(length=2048), nullable=True),
        sa.Column('title', sa.String(length=512), nullable=False),
        sa.Column('source', sa.String(length=255), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('snippet', sa.Text(), nullable=True),
        sa.Column('provider_name', sa.String(length=50), nullable=True),
        sa.Column('fetch_status', sa.String(length=50), nullable=True),
        sa.Column('fetch_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_articles_id'), 'articles', ['id'], unique=False)
    op.create_index(op.f('ix_articles_url'), 'articles', ['url'], unique=False)
    op.create_index(op.f('ix_articles_canonical_url'), 'articles', ['canonical_url'], unique=False)
    op.create_index(op.f('ix_articles_published_at'), 'articles', ['published_at'], unique=False)

    # Extracted Contents
    op.create_table(
        'extracted_contents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('language', sa.String(length=10), nullable=True),
        sa.Column('extraction_method', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('article_id')
    )
    op.create_index(op.f('ix_extracted_contents_id'), 'extracted_contents', ['id'], unique=False)
    op.create_index(op.f('ix_extracted_contents_content_hash'), 'extracted_contents', ['content_hash'], unique=False)

    # Mentions
    op.create_table(
        'mentions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('director_id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('sentiment', sa.Enum('POSITIVE', 'NEGATIVE', 'NEUTRAL', 'MIXED', name='sentiment'), nullable=False),
        sa.Column('severity', sa.Enum('LOW', 'MEDIUM', 'HIGH', name='severity'), nullable=False),
        sa.Column('category', sa.Enum('REGULATORY_ENFORCEMENT', 'LEGAL_COURT', 'FINANCIAL_CORPORATE', 'GOVERNANCE_BOARD_APPOINTMENT', 'AWARDS_RECOGNITION', 'PERSONAL_REPUTATION', 'OTHER', name='category'), nullable=False),
        sa.Column('summary_bullets', sa.JSON(), nullable=True),
        sa.Column('why_it_matters', sa.Text(), nullable=True),
        sa.Column('is_reviewed', sa.Boolean(), nullable=True),
        sa.Column('is_confirmed', sa.Boolean(), nullable=True),
        sa.Column('alert_sent', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ),
        sa.ForeignKeyConstraint(['director_id'], ['directors.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_mentions_id'), 'mentions', ['id'], unique=False)
    op.create_index(op.f('ix_mentions_director_id'), 'mentions', ['director_id'], unique=False)
    op.create_index(op.f('ix_mentions_article_id'), 'mentions', ['article_id'], unique=False)
    op.create_index(op.f('ix_mentions_confidence'), 'mentions', ['confidence'], unique=False)
    op.create_index(op.f('ix_mentions_created_at'), 'mentions', ['created_at'], unique=False)
    op.create_index('idx_mention_sentiment_severity', 'mentions', ['sentiment', 'severity'], unique=False)

    # Reports
    op.create_table(
        'reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('report_date', sa.Date(), nullable=False),
        sa.Column('html_path', sa.String(length=512), nullable=True),
        sa.Column('pdf_path', sa.String(length=512), nullable=True),
        sa.Column('stats', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reports_id'), 'reports', ['id'], unique=False)
    op.create_index(op.f('ix_reports_report_date'), 'reports', ['report_date'], unique=True)

    # Users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('role', sa.Enum('ADMIN', 'MD', name='userrole'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Settings
    op.create_table(
        'settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_settings_id'), 'settings', ['id'], unique=False)
    op.create_index(op.f('ix_settings_key'), 'settings', ['key'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_settings_key'), table_name='settings')
    op.drop_index(op.f('ix_settings_id'), table_name='settings')
    op.drop_table('settings')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_reports_report_date'), table_name='reports')
    op.drop_index(op.f('ix_reports_id'), table_name='reports')
    op.drop_table('reports')
    op.drop_index('idx_mention_sentiment_severity', table_name='mentions')
    op.drop_index(op.f('ix_mentions_created_at'), table_name='mentions')
    op.drop_index(op.f('ix_mentions_confidence'), table_name='mentions')
    op.drop_index(op.f('ix_mentions_article_id'), table_name='mentions')
    op.drop_index(op.f('ix_mentions_director_id'), table_name='mentions')
    op.drop_index(op.f('ix_mentions_id'), table_name='mentions')
    op.drop_table('mentions')
    op.drop_index(op.f('ix_extracted_contents_content_hash'), table_name='extracted_contents')
    op.drop_index(op.f('ix_extracted_contents_id'), table_name='extracted_contents')
    op.drop_table('extracted_contents')
    op.drop_index(op.f('ix_articles_published_at'), table_name='articles')
    op.drop_index(op.f('ix_articles_canonical_url'), table_name='articles')
    op.drop_index(op.f('ix_articles_url'), table_name='articles')
    op.drop_index(op.f('ix_articles_id'), table_name='articles')
    op.drop_table('articles')
    op.drop_index(op.f('ix_directors_full_name'), table_name='directors')
    op.drop_index(op.f('ix_directors_id'), table_name='directors')
    op.drop_table('directors')

