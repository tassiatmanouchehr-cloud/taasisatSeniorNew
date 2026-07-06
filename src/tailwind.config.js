/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './ui/components/**/*.html',
    './ui/layouts/**/*.html',
    './ui/js/**/*.js',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      // Design tokens will be added in Commit 2
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
};
