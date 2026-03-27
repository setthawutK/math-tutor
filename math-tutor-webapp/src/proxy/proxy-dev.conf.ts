const mathTutorService = '';

const PROXY_CONFIG = {
  'mathtutor-service': {
    target: mathTutorService,
    changeOrigin: true,
    secure: false,
    pathRewrite: {
      '^mathtutor-service': '',
    },
  },
};

module.exports = PROXY_CONFIG;
