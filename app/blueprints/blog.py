"""
Blog / Travel Guides blueprint — Phase 4.
Admin-authored destination articles and travel guides.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import BlogPost
from app.services.auth import get_current_user, roles_required
from app import db
from datetime import datetime
import re

# ── HTML sanitisation (bleach) ────────────────────────────────────────────────
# Allowed tags for rich blog content — scripts, iframes, and event handlers
# are stripped to prevent stored XSS.
try:
    import bleach
    _ALLOWED_TAGS = [
        'p', 'br', 'strong', 'em', 'b', 'i', 'u', 's',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'blockquote', 'pre', 'code',
        'a', 'img',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'hr', 'div', 'span',
    ]
    _ALLOWED_ATTRS = {
        'a':   ['href', 'title', 'target', 'rel'],
        'img': ['src', 'alt', 'width', 'height'],
        '*':   ['class'],
    }
    def sanitize_html(html: str) -> str:
        """Strip dangerous tags/attributes from admin-submitted HTML."""
        return bleach.clean(
            html,
            tags=_ALLOWED_TAGS,
            attributes=_ALLOWED_ATTRS,
            protocols=['http', 'https', 'mailto'],  # blocks javascript: URIs
            strip=True,
        )
except ImportError:
    # bleach not installed — fall back to plain-text (no HTML rendered)
    import html as _html
    def sanitize_html(html_str: str) -> str:
        return _html.escape(html_str)

blog_bp = Blueprint('blog', __name__, url_prefix='/travel-guides')


def slugify(text):
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text.strip('-')


@blog_bp.route('/')
def listing():
    category = request.args.get('category', '').strip()
    destination = request.args.get('destination', '').strip()
    query = BlogPost.query.filter_by(published=True)
    if category:
        query = query.filter_by(category=category)
    if destination:
        query = query.filter(BlogPost.destination.ilike(f'%{destination}%'))
    posts = query.order_by(BlogPost.published_at.desc()).all()
    categories = db.session.query(BlogPost.category).distinct().all()
    categories = [c[0] for c in categories]
    user = get_current_user()
    return render_template('blog_listing.html', posts=posts, user=user,
                           categories=categories, active_category=category,
                           destination=destination)


@blog_bp.route('/<slug>')
def detail(slug):
    post = BlogPost.query.filter_by(slug=slug, published=True).first_or_404()
    # Increment views
    post.views = (post.views or 0) + 1
    db.session.commit()
    # Related posts
    related = BlogPost.query.filter(
        BlogPost.published == True,
        BlogPost.id != post.id,
        BlogPost.destination == post.destination
    ).limit(3).all()
    if len(related) < 3:
        more = BlogPost.query.filter(
            BlogPost.published == True,
            BlogPost.id != post.id,
            BlogPost.category == post.category
        ).limit(3 - len(related)).all()
        related += more
    user = get_current_user()
    return render_template('blog_detail.html', post=post, related=related, user=user)


# ---- Admin CRUD for blog posts ---------------------------------------------

@blog_bp.route('/admin')
@roles_required('admin')
def admin_list():
    user = get_current_user()
    posts = BlogPost.query.order_by(BlogPost.id.desc()).all()
    return render_template('admin_blog.html', user=user, posts=posts)


@blog_bp.route('/admin/new', methods=['GET', 'POST'])
@roles_required('admin')
def admin_new():
    user = get_current_user()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        if not title:
            flash('Title is required.', 'danger')
            return redirect(url_for('blog.admin_new'))

        slug = slugify(title)
        # Ensure uniqueness
        base_slug = slug
        counter = 1
        while BlogPost.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        post = BlogPost(
            title=title,
            slug=slug,
            destination=request.form.get('destination', ''),
            category=request.form.get('category', 'Guide'),
            excerpt=request.form.get('excerpt', ''),
            content=sanitize_html(request.form.get('content', '')),
            featured_image=request.form.get('featured_image', ''),
            author=request.form.get('author', 'SnapTravels Team'),
            published=bool(request.form.get('published')),
            published_at=datetime.utcnow() if request.form.get('published') else None,
        )
        tags_raw = request.form.get('tags', '')
        post.tags = [t.strip() for t in tags_raw.split(',') if t.strip()]
        db.session.add(post)
        db.session.commit()
        flash(f'Post "{title}" created!', 'success')
        return redirect(url_for('blog.listing'))

    return render_template('blog_admin_form.html', user=user, post=None)


@blog_bp.route('/admin/<int:post_id>/edit', methods=['GET', 'POST'])
@roles_required('admin')
def admin_edit(post_id):
    post = BlogPost.query.get_or_404(post_id)
    user = get_current_user()
    if request.method == 'POST':
        post.title = request.form.get('title', post.title)
        post.destination = request.form.get('destination', '')
        post.category = request.form.get('category', 'Guide')
        post.excerpt = request.form.get('excerpt', '')
        post.content = sanitize_html(request.form.get('content', ''))
        post.featured_image = request.form.get('featured_image', '')
        post.author = request.form.get('author', 'SnapTravels Team')
        was_published = post.published
        post.published = bool(request.form.get('published'))
        if post.published and not was_published:
            post.published_at = datetime.utcnow()
        tags_raw = request.form.get('tags', '')
        post.tags = [t.strip() for t in tags_raw.split(',') if t.strip()]
        db.session.commit()
        flash('Post updated!', 'success')
        return redirect(url_for('blog.detail', slug=post.slug))
    return render_template('blog_admin_form.html', user=user, post=post)
