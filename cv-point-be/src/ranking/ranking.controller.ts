import {
  Controller,
  Post,
  UploadedFiles,
  UseInterceptors,
  Body,
} from '@nestjs/common';
import { FilesInterceptor } from '@nestjs/platform-express';
import { RankingService } from './ranking.service';

@Controller('ranking')
export class RankingController {
  constructor(private readonly rankingService: RankingService) {}

  @Post('upload')
  @UseInterceptors(FilesInterceptor('cvs'))
  async uploadCVs(
    @UploadedFiles() files: Express.Multer.File[],
    @Body('jd') jd: string,
  ) {
    return this.rankingService.rankFiles(files, jd);
  }
}