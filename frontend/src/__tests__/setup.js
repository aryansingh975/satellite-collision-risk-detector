// Polyfill browser APIs that Cesium requires but jsdom does not provide
if (typeof global.Worker === "undefined") {
  global.Worker = class Worker {
    constructor() {}
    postMessage() {}
    terminate() {}
    addEventListener() {}
    removeEventListener() {}
  };
}
