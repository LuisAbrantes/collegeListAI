import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vite.dev/config/
export default defineConfig({
    plugins: [react()],
    server: {
        allowedHosts: [
            'verena-unscrupulous-worshippingly.ngrok-free.dev',
            '.ngrok-free.app' // Permite todos os subdomínios ngrok gratuitos (mais prático)
        ]
    }
});
