import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class MathTutorService {
  private readonly _httpClient: HttpClient = inject(HttpClient);

  askQuestion(
    session_id: string,
    question: string,
    model: string,
  ): Observable<{ explanation: string; image: string[]; wolfram_raw: string }> {
    return this._httpClient.post<{ explanation: string; image: string[]; wolfram_raw: string }>(
      'http://127.0.0.1:8000/ask',
      { session_id, question, model },
    );
  }
}
