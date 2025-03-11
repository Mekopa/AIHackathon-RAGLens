/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: 'var(--color-primary)',
        'primary-hover': 'var(--color-primary-hover)',
        'deactivate': 'var(--color-deactivate)',
        secondary: 'var(--color-secondary)',
        accent: 'var(--color-accent)',
        background: 'var(--color-background)',
        surface: 'var(--color-surface)',
        text: 'var(--color-text)',
        'text-secondary': 'var(--color-text-secondary)',
        border: 'var(--color-border)',
        input: 'var(--color-input)',
        'input-border': 'var(--color-input-border)',
        'input-focus': 'var(--color-input-focus)',
        error: 'var(--color-error)',
      },
      typography: {
        DEFAULT: {
          css: {
            maxWidth: 'none',
            color: 'var(--color-text)',
            '--tw-prose-headings': 'var(--color-text)',
            '--tw-prose-body': 'var(--color-text)',
          },
        },
      },
    },
  },
  plugins: [],
};