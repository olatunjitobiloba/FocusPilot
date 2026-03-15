module.exports = {
  devServer: (devServerConfig) => {
    devServerConfig.client = devServerConfig.client || {};
    devServerConfig.client.overlay = false;
    return devServerConfig;
  },
  jest: {
    configure: {
      testEnvironment: "jsdom",
      setupFilesAfterEnv: ["<rootDir>/src/setupTests.ts"],
      moduleNameMapper: {
        "^axios$": "<rootDir>/__mocks__/axios.js",
        "^react-router-dom$": "<rootDir>/__mocks__/react-router-dom.js",
        "\\.(css|less|scss|sass)$": "<rootDir>/__mocks__/styleMock.js"
      },
      transformIgnorePatterns: [
        "node_modules/(?!(msw|@mswjs|until-async)/)"
      ]
    }
  }
};
