"""Add India-specific fields

Revision ID: 002
Revises: 001
Create Date: 2024-01-17 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update category enum to include new India-specific categories
    # PostgreSQL enum alteration (handle errors gracefully if values already exist)
    connection = op.get_bind()
    # Check existing enum values
    result = connection.execute(sa.text("SELECT enumlabel FROM pg_enum WHERE enumtypid = 'category'::regtype"))
    existing_values = [row[0] for row in result]
    
    if 'LITIGATION' not in existing_values:
        op.execute("ALTER TYPE category ADD VALUE 'LITIGATION'")
    if 'CORPORATE_GOVERNANCE' not in existing_values:
        op.execute("ALTER TYPE category ADD VALUE 'CORPORATE_GOVERNANCE'")
    if 'ESG_SOCIAL_POLITICAL' not in existing_values:
        op.execute("ALTER TYPE category ADD VALUE 'ESG_SOCIAL_POLITICAL'")
    
    # Add India-specific fields to articles table
    op.add_column('articles', sa.Column('language', sa.String(length=10), nullable=True, server_default='en'))
    op.add_column('articles', sa.Column('country', sa.String(length=2), nullable=True, server_default='IN'))
    op.add_column('articles', sa.Column('state', sa.String(length=100), nullable=True))
    op.add_column('articles', sa.Column('district', sa.String(length=100), nullable=True))
    op.add_column('articles', sa.Column('city', sa.String(length=100), nullable=True))
    op.add_column('articles', sa.Column('source_type', sa.String(length=50), nullable=True))
    op.add_column('articles', sa.Column('source_trust_score', sa.Integer(), nullable=True, server_default='50'))
    
    # Create indexes for new fields
    op.create_index('idx_article_language', 'articles', ['language'])
    op.create_index('idx_article_country', 'articles', ['country'])
    op.create_index('idx_article_state', 'articles', ['state'])
    op.create_index('idx_article_language_country', 'articles', ['language', 'country'])
    op.create_index('idx_article_state_district', 'articles', ['state', 'district'])
    
    # Add India-specific fields to directors table
    op.add_column('directors', sa.Column('first_name', sa.String(length=100), nullable=True))
    op.add_column('directors', sa.Column('middle_names', sa.String(length=200), nullable=True))
    op.add_column('directors', sa.Column('last_name', sa.String(length=100), nullable=True))
    op.add_column('directors', sa.Column('company_name', sa.String(length=255), nullable=True))
    op.add_column('directors', sa.Column('company_industry', sa.String(length=100), nullable=True))
    op.add_column('directors', sa.Column('listed_exchange', sa.String(length=50), nullable=True))
    op.add_column('directors', sa.Column('hq_state', sa.String(length=100), nullable=True))
    op.add_column('directors', sa.Column('hq_city', sa.String(length=100), nullable=True))
    op.add_column('directors', sa.Column('india_context_profile', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('directors', sa.Column('provider_newsdata_enabled', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('directors', sa.Column('provider_newsapi_ai_enabled', sa.Boolean(), nullable=True, server_default='false'))
    
    # Update extracted_contents to ensure language field exists (may already exist)
    # Check if column exists first - this is safe
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('extracted_contents')]
    if 'language' not in columns:
        op.add_column('extracted_contents', sa.Column('language', sa.String(length=10), nullable=True, server_default='en'))


def downgrade() -> None:
    # Remove indexes
    op.drop_index('idx_article_state_district', table_name='articles')
    op.drop_index('idx_article_language_country', table_name='articles')
    op.drop_index('idx_article_state', table_name='articles')
    op.drop_index('idx_article_country', table_name='articles')
    op.drop_index('idx_article_language', table_name='articles')
    
    # Remove columns from articles
    op.drop_column('articles', 'source_trust_score')
    op.drop_column('articles', 'source_type')
    op.drop_column('articles', 'city')
    op.drop_column('articles', 'district')
    op.drop_column('articles', 'state')
    op.drop_column('articles', 'country')
    op.drop_column('articles', 'language')
    
    # Remove columns from directors
    op.drop_column('directors', 'provider_newsapi_ai_enabled')
    op.drop_column('directors', 'provider_newsdata_enabled')
    op.drop_column('directors', 'india_context_profile')
    op.drop_column('directors', 'hq_city')
    op.drop_column('directors', 'hq_state')
    op.drop_column('directors', 'listed_exchange')
    op.drop_column('directors', 'company_industry')
    op.drop_column('directors', 'company_name')
    op.drop_column('directors', 'last_name')
    op.drop_column('directors', 'middle_names')
    op.drop_column('directors', 'first_name')

