function slugify(text) {
  return text
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]/g, '-')
    .replace(/^-|-$/g, '');
}

function truncateSlug(slug, max) {
  if (slug.length <= max) return slug;
  return slug.slice(0, max).replace(/-$/, '');
}

module.exports = { slugify, truncateSlug };
