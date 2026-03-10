import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { ChangeDetectorRef } from '@angular/core';
import { API_BASE_URL } from '../config';

@Component({
  selector: 'app-upload',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './upload.html',
  styleUrls: ['./upload.css']
})
export class UploadComponent {

  selectedFile: File | null = null;

  isUploading = false;

  transcriptText: string = '';
  downloadUrl: string = '';

  videoUrl: string = '';

  progress = 0;
  progressTimer: any;
  videoId: string = '';

  radius = 15;
  circumference = 2 * Math.PI * this.radius;
  offset = this.circumference;

  // ⭐ NEW
  fileTypeIcon = "";
  statusMessage = "";

  constructor(private http: HttpClient, private cd: ChangeDetectorRef) {}

  onFileSelected(event: any) {

    this.selectedFile = event.target.files[0];

    if (!this.selectedFile) return;

    const name = this.selectedFile.name.toLowerCase();

    if (name.endsWith(".mp4") || name.endsWith(".mov") || name.endsWith(".avi") || name.endsWith(".mkv")) {
      this.fileTypeIcon = "🎥";
      this.statusMessage = "Video detected. Click upload to generate transcript.";
    }

    else if (name.endsWith(".pdf")) {
      this.fileTypeIcon = "📕";
      this.statusMessage = "PDF detected. Video will be generated from document.";
    }

    else if (name.endsWith(".docx")) {
      this.fileTypeIcon = "📘";
      this.statusMessage = "Word document detected. Video will be generated.";
    }

    else if (name.endsWith(".txt")) {
      this.fileTypeIcon = "📄";
      this.statusMessage = "Text document detected. Video will be generated.";
    }

    else {
      this.fileTypeIcon = "❓";
      this.statusMessage = "Unsupported file type.";
    }

  }

  uploadFile() {

    if (!this.selectedFile) {
      alert("Please select a file");
      return;
    }

    const fileName = this.selectedFile.name.toLowerCase();

    const isVideo =
      fileName.endsWith(".mp4") ||
      fileName.endsWith(".mov") ||
      fileName.endsWith(".avi") ||
      fileName.endsWith(".mkv");

    const isDocument =
      fileName.endsWith(".txt") ||
      fileName.endsWith(".pdf") ||
      fileName.endsWith(".docx");

    if (isVideo) {
      this.uploadVideo();
    }
    else if (isDocument) {
      this.generateVideoFromDocument();
    }
    else {
      alert("Unsupported file type");
    }

  }

  uploadVideo() {

    if (!this.selectedFile) return;

    if (this.progressTimer) {
      clearInterval(this.progressTimer);
    }

    this.transcriptText = '';
    this.downloadUrl = '';
    this.videoUrl = '';
    this.progress = 0;
    this.offset = this.circumference;
    this.videoId = '';

    this.statusMessage = "Uploading video...";

    const formData = new FormData();
    formData.append("file", this.selectedFile);

    this.isUploading = true;

    this.http.post<any>(
      `${API_BASE_URL}/upload-video`,
      formData
    ).subscribe({
      next: (res) => {

        this.videoId = res.video_id;
        this.statusMessage = "Transcribing video...";
        this.startProgressPolling();

      },
      error: (err) => {
        console.error(err);
        this.isUploading = false;
      }
    });
  }

  generateVideoFromDocument() {

    if (!this.selectedFile) return;

    const formData = new FormData();
    formData.append("file", this.selectedFile);

    this.isUploading = true;
    this.transcriptText = '';
    this.videoUrl = '';

    this.statusMessage = "Generating video from document...";

    this.http.post<any>(
      `${API_BASE_URL}/generate-video-from-document`,
      formData
    ).subscribe({
      next: (res) => {

        this.videoUrl =
          `${API_BASE_URL}${res.download_url}`;

        this.statusMessage = "Video generated successfully.";

        this.isUploading = false;
        this.cd.detectChanges();

      },
      error: (err) => {
        console.error(err);
        this.isUploading = false;
      }
    });

  }

  startProgressPolling() {

    this.progressTimer = setInterval(() => {

      this.http.get<any>(`${API_BASE_URL}/progress/${this.videoId}`)
        .subscribe(res => {

          this.progress = res.progress;

          this.offset =
            this.circumference -
            (this.progress / 100) * this.circumference;

          this.cd.detectChanges();

          if (this.progress >= 100) {

            clearInterval(this.progressTimer);

            const transcriptApi =
              `${API_BASE_URL}/transcript/${this.videoId}`;

            this.http.get<any>(transcriptApi)
              .subscribe(data => {

                this.transcriptText = data.transcript;

                this.downloadUrl =
                  `${API_BASE_URL}/download/${this.videoId}`;

                this.statusMessage = "Transcription completed.";

                this.isUploading = false;

                this.cd.detectChanges();

              });

          }

        });

    }, 500);

  }

}