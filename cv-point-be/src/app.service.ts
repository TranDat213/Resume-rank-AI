import { Injectable } from '@nestjs/common';
import { PrismaService } from './prisma/prisma.service';
import axios from 'axios';

@Injectable()
export class AppService {
  constructor(private prisma: PrismaService) {}

  getHello(): string {
    return 'Hello World!';
  }

  async getHealth() {
    let dbStatus = 'disconnected';
    let aiStatus = 'disconnected';
    let aiDetails = null;
    let globalStatus = 'ok';
    const errors: any[] = [];

    try {
      await this.prisma.$queryRaw`SELECT 1`;
      dbStatus = 'connected';
    } catch (error) {
      globalStatus = 'error';
      errors.push({ service: 'database', message: error.message });
    }

    try {
      const res = await axios.get('http://localhost:5000/health', { timeout: 3000 });
      if (res.status === 200) {
        aiStatus = 'connected';
        aiDetails = res.data;
      } else {
        globalStatus = 'error';
        errors.push({ service: 'ai-service', message: `HTTP ${res.status}` });
      }
    } catch (error) {
      globalStatus = 'error';
      errors.push({ service: 'ai-service', message: error.message });
    }

    return { 
      status: globalStatus,
      database: dbStatus, 
      aiService: aiStatus,
      aiDetails: aiDetails,
      errors: errors.length > 0 ? errors : undefined,
      timestamp: new Date().toISOString() 
    };
  }
}

