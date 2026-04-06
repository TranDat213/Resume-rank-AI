import { Injectable } from '@nestjs/common';
import axios from 'axios';
import FormData from 'form-data';
import { PrismaService } from '../prisma/prisma.service';
import * as fs from 'fs/promises';
import * as path from 'path';
import { randomUUID } from 'crypto';

@Injectable()
export class RankingService {
  constructor(private prisma: PrismaService) {}

  async rankFiles(files: Express.Multer.File[], jd: string, userId: string) {
    const form = new FormData();
    form.append('jd', jd);

    files.forEach((file) => {
      form.append('cvs', file.buffer, file.originalname);
    });

    const res = await axios.post('http://localhost:5000/rank', form, {
      headers: form.getHeaders(),
    });

    const data = res.data;
    const jdInfo = data.jd_info;
    const results = data.results;

    // Ensure uploads directory exists in OS temp to avoid triggering Live Server reloads
    const uploadsDir = path.join(require('os').tmpdir(), 'cv_AI_project_uploads');
    try {
      await fs.access(uploadsDir);
    } catch {
      await fs.mkdir(uploadsDir, { recursive: true });
    }

    // Save JobDescription record
    const jobDescription = await this.prisma.jobDescription.create({
      data: {
        user_id: userId,
        title: 'Uploaded Job Description',
        description: jdInfo?.description || jd,
        required_skills: jdInfo?.required_skills || [],
        required_years: jdInfo?.required_years || 0,
        required_education_level: jdInfo?.required_education_level || 0,
      },
    });

    for (const [index, result] of results.entries()) {
      const originalFile = files.find(f => f.originalname === result.filename) || files[index];

      // Save file physically
      const uniqueFilename = `${randomUUID()}-${originalFile.originalname}`;
      const filePath = path.join(uploadsDir, uniqueFilename);
      await fs.writeFile(filePath, originalFile.buffer);
      const fileUrl = `/uploads/${uniqueFilename}`;

      const extractedInfo = result.extracted_info || {};

      const cv = await this.prisma.cV.create({
        data: {
          user_id: userId,
          file_url: fileUrl,
          file_name: originalFile.originalname,
          content: extractedInfo.text || '',
          skills: extractedInfo.skills || [],
          companies: extractedInfo.companies || [],
          roles: [], 
          education_level: extractedInfo.education_level || 0,
          years_experience: extractedInfo.years_experience || 0,
        },
      });

      const score = result.score || 0;
      let matchLevel = 'LOW';
      if (score >= 70) matchLevel = 'HIGH';
      else if (score >= 40) matchLevel = 'MEDIUM';

      await this.prisma.rankingResult.create({
        data: {
          id: randomUUID(),
          jd_id: jobDescription.id,
          cv_id: cv.id,
          score: score,
          matched_skills: result.matched_skills || [],
          missed_skills: result.missing_skills || [],
          match_level: matchLevel as any,
          updated_at: new Date(),
        },
      });
    }

    return { jd_info: jdInfo, results };
  }
}
