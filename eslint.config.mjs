import globals from 'globals';
import js from '@eslint/js';

export default [
    js.configs.recommended,
    {
        files: ['**/*.js', '**/*.mjs', '**/*.jsx'],
        languageOptions: {
            ecmaVersion: 2022,
            sourceType: 'module',
            globals: {
                ...globals.browser,
                ...globals.node,
                console: 'readonly'
            }
        },
        rules: {
            'no-unused-vars': 'error',
            'no-var': 'error',
            'prefer-const': 'warn'
        }
    }
];
