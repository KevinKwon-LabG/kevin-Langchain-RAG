# ollama

Ollama  Container<br/><br/>

Docker Volume: vol-dev-ollama-v1.0 <br/>
Docker Network: dev_network<br/>
Docker run (with GPU)<br/>
docker run -d \<br/>
  --name ollama \<br/>
  --network dev_network \<br/>
  --gpus=all \<br/>
  -v vol-dev-ollama-v1.0:/root/.ollama \<br/>
  -p 11434:11434 \<br/>
  ollama/ollama<br/><br/>



Ollama  Models<br/><br/>


Model Name: Gemma3:12b-it-qua<br/>
Model	Size 약 9GB	<br/>

Google DeepMind가 공개한 최신 대규모 생성형 AI 언어 모델(Gemma 3)의 120억 파라미터(12B) 지시형 튜닝(Instruction Tuned) 버전이며, QAT(Quantization Aware Training, 양자화 인지 학습) 기법이 적용된 변형 모델입니다.<br/><br/>

**모델 규모**: 120억 파라미터(12B)<br/>
**아키텍처**: 고급 Transformer 구조 기반<br/>
**지시형 튜닝(IT)**: 명령어에 최적화된 학습으로 높은 정확도와 활용 편의성 제공<br/>
**양자화 인지 학습(QAT)**: 모델 학습 중 양자화를 도입해 성능 저하 없이 모델을 매우 경량화함<br/>
**오픈소스**: 자유로운 연구·상용화 허용, 커스터마이징과 파인튜닝 지원<br/>
**다국어 지원**: 약 140여 개 이상의 언어에 대응<br/>
**높은 효율성**: 단일 GPU (예: NVIDIA A100, RTX 3090, RTX 4060)에서도 실행 가능하며 VRAM 요구량이 대폭 절감됨<br/>
**컨텍스트 윈도우**: 8K 토큰 지원<br/>
**양자화 옵션**: INT8, INT4 등 다양한 양자화 지원 — INT4 및 QAT 모델은 강력한 경량화와 동시에 품질 저하가 현저히 적음<br/>
		

