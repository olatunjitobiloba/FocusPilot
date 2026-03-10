// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

// Add missing Node.js globals for MSW
import { TextEncoder, TextDecoder } from 'util';
import { ReadableStream, TransformStream } from 'web-streams-polyfill';

global.TextEncoder = TextEncoder as any;
global.TextDecoder = TextDecoder as any;
(global as any).ReadableStream = ReadableStream;
(global as any).TransformStream = TransformStream;
