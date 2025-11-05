export interface RuntimeEnv {
  API_URL: string;
  [key: string]: unknown;
}

const globalWindow = window as unknown as Record<string, unknown>;
const defaultEnv: RuntimeEnv = {
  API_URL: 'http://localhost:8000',
};

export const runtimeEnv: RuntimeEnv = {
  ...defaultEnv,
  ...(globalWindow['__env'] as Partial<RuntimeEnv>),
};
