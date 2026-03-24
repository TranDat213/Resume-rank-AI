import { Module } from '@nestjs/common';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { CvModule } from './cv/cv.module';
import { JdModule } from './jd/jd.module';
import { RankingModule } from './ranking/ranking.module';

@Module({
  imports: [CvModule, JdModule, RankingModule],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
