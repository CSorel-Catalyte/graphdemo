import '@testing-library/jest-dom';

// Mock window.ResizeObserver
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => {},
  }),
});

// Mock WebGL context for Three.js
const mockWebGLContext = {
  canvas: document.createElement('canvas'),
  getExtension: () => null,
  getParameter: () => null,
  createShader: () => null,
  shaderSource: () => {},
  compileShader: () => {},
  createProgram: () => null,
  attachShader: () => {},
  linkProgram: () => {},
  useProgram: () => {},
  createBuffer: () => null,
  bindBuffer: () => {},
  bufferData: () => {},
  enableVertexAttribArray: () => {},
  vertexAttribPointer: () => {},
  drawArrays: () => {},
  viewport: () => {},
  clearColor: () => {},
  clear: () => {},
};

HTMLCanvasElement.prototype.getContext = (contextType: string) => {
  if (contextType === 'webgl' || contextType === 'webgl2') {
    return mockWebGLContext;
  }
  return null;
};