import { Injectable } from '@nestjs/common';
import axios from 'axios';
import FormData from 'form-data';

@Injectable()
export class RankingService {
  async rankFiles(files: Express.Multer.File[], jd: string) {
    const form = new FormData();
    form.append('jd', jd);

    files.forEach((file) => {
      form.append('cvs', file.buffer, file.originalname);
    });

    const res = await axios.post('http://localhost:5000/rank', form, {
      headers: form.getHeaders(),
    });

    return res.data;
  }
}