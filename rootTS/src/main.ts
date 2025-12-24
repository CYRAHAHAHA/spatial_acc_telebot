import { app } from './app';
import winston from 'winston';
import path from 'path';
import fs from 'fs';

const logDir = path.resolve(__dirname, '../logs');
if (!process.env.RAILWAY_ENVIRONMENT && !fs.existsSync(logDir)) fs.mkdirSync(logDir, { recursive: true });

const logger = winston.createLogger({
    level: 'info',
    format: winston.format.combine(winston.format.timestamp(), winston.format.json()),
    transports: [new winston.transports.Console()]
});

const port = parseInt(process.env.PORT || "8080", 10);
app.listen(port, "0.0.0.0", () => {
    logger.info(`Server running on port ${port}`);
});