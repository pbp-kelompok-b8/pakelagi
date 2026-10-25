const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests/browser',
  use: { baseURL: 'http://127.0.0.1:8765' },
  webServer: {
    command: 'python manage.py runserver 127.0.0.1:8765 --noreload',
    url: 'http://127.0.0.1:8765',
    reuseExistingServer: !process.env.CI,
  },
});
