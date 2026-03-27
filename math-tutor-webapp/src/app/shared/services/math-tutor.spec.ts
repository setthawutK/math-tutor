import { TestBed } from '@angular/core/testing';

import { MathTutor } from './math-tutor';

describe('MathTutor', () => {
  let service: MathTutor;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(MathTutor);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
