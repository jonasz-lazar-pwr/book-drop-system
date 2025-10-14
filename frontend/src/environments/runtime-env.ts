export interface RuntimeEnv {
  apiUrl: string;
  [key: string]: unknown;
}

const globalWindow = window as unknown as Record<string, unknown>;
const defaultEnv: RuntimeEnv = {
  apiUrl: 'http://localhost:8000',
};

export const runtimeEnv: RuntimeEnv = {
  ...defaultEnv,
  ...(globalWindow['__env'] as Partial<RuntimeEnv>),
};
