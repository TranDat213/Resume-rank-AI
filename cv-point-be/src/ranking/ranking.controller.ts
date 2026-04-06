import {
  Controller,
  Post,
  UploadedFiles,
  UseInterceptors,
  Body,
  UseGuards,
  Req,
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
    @Req() req: any,
  ) {
    const userId = req.user.userId;
    return this.rankingService.rankFiles(files, jd, userId);
  }
}