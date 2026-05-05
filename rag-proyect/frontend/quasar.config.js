/* eslint-env node */
module.exports = function (/* ctx */) {
  return {
    boot: [],

    css: ['app.scss'],

    extras: ['roboto-font', 'material-icons'],

    build: {
      vueRouterMode: 'hash',
      target: {
        browser: ['es2019', 'edge88', 'firefox78', 'chrome87', 'safari13.1'],
        node: 'node20',
      },
    },

    devServer: {
      open: false,
      port: 9000,
      host: '0.0.0.0',
      proxy: {
        '/ask': {
          target: process.env.API_TARGET || 'http://localhost:8000',
          changeOrigin: true,
        },
        '/health': {
          target: process.env.API_TARGET || 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },

    framework: {
      config: {},
      plugins: ['Notify'],
    },
  }
}
