import {
  Controller,
  Post,
  UploadedFiles,
  UseInterceptors,
  Body,
  UseGuards,
} from '@nestjs/common';
import { FilesInterceptor } from '@nestjs/platform-express';
import { RankingService } from './ranking.service';
import { AuthGuard } from '@nestjs/passport';

@Controller('ranking')
export class RankingController {
  constructor(private readonly rankingService: RankingService) {}

  @Post('upload')
  @UseGuards(AuthGuard('jwt'))
  @UseInterceptors(FilesInterceptor('cvs'))
  async uploadCVs(
    @UploadedFiles() files: Express.Multer.File[],
    @Body('jd') jd: string,
  ) {
    return this.rankingService.rankFiles(files, jd);
  }
}