import tseslint from 'typescript-eslint';
export default tseslint.config({files:['src/**/*.{ts,tsx}'],languageOptions:{parser:tseslint.parser},plugins:{'@typescript-eslint':tseslint.plugin},rules:{'@typescript-eslint/no-explicit-any':'error','@typescript-eslint/no-unused-vars':['error',{argsIgnorePattern:'^_',varsIgnorePattern:'^_'}]}});
