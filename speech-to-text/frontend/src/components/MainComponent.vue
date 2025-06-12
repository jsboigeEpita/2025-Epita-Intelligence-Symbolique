<template>
  <v-app>
    <!-- App Bar -->
    <v-app-bar app dark elevation="4">
      <v-icon class="ml-3">mdi-bullhorn-variant</v-icon>
      <v-toolbar-title class="text-h5">
        Argument Analyzer
      </v-toolbar-title>
      <v-spacer></v-spacer>
      <v-btn icon>
        <v-icon>mdi-help-circle-outline</v-icon>
      </v-btn>
    </v-app-bar>

    <!-- Main Content -->
    <v-main>
      <div class="gradient-bg pa-4" style="min-height: 200px;">
        <v-container>
          <v-row justify="center">
            <v-col cols="12" md="8">
              <div class="text-center white--text mb-6">
                <h1 class="display-1 font-weight-light mb-2">
                  Analyze Arguments with AI
                </h1>
                <p class="text-h6 font-weight-light">
                  Upload audio or paste a YouTube link to detect logical fallacies and analyze argument structure
                </p>
              </div>
            </v-col>
          </v-row>
        </v-container>
      </div>

      <v-container class="mt-n12">
        <!-- Input Card -->
        <v-row justify="center">
          <v-col cols="12" md="10" lg="8">
            <v-card class="card-shadow" elevation="0">
              <v-card-text class="pa-6">
                <!-- Input Type Selector -->
                <v-tabs v-model="inputType" color="primary" class="mb-6" centered>
                  <v-tab>
                    <v-icon left>mdi-file-music</v-icon>
                    Audio File
                  </v-tab>
                  <v-tab>
                    <v-icon left>mdi-youtube</v-icon>
                    YouTube Link
                  </v-tab>
                </v-tabs>

                <v-tabs-items v-model="inputType">
                  <!-- Audio File Upload Tab -->
                  <v-tab-item v-if="inputType === 0">
                    <v-file-input v-model="audioFile" accept="audio/*" label="Upload Audio File"
                      prepend-icon="mdi-file-music" show-size outlined :loading="processing"
                      :disabled="processing"></v-file-input>
                  </v-tab-item>

                  <!-- YouTube Link Tab -->
                  <v-tab-item v-if="inputType === 1">
                    <v-text-field v-model="youtubeUrl" label="YouTube Video URL" prepend-icon="mdi-youtube"
                      placeholder="https://www.youtube.com/watch?v=..." outlined :loading="processing"
                      :disabled="processing" :rules="[urlValidation]"></v-text-field>
                  </v-tab-item>
                </v-tabs-items>

                <!-- Analysis Options -->
                <v-row class="mt-4">
                  <v-col cols="12" md="6">
                    <v-checkbox v-model="analysisOptions.detectFallacies" label="Detect Logical Fallacies"
                      color="primary"></v-checkbox>
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-checkbox v-model="analysisOptions.analyzeStructure" label="Analyze Structure"
                      color="primary"></v-checkbox>
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-checkbox v-model="analysisOptions.evaluateCoherence" label="Evaluate Coherence"
                      color="primary"></v-checkbox>
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-checkbox v-model="analysisOptions.includeContext" label="Include Context in Analysis"
                      color="primary"></v-checkbox>
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-text-field v-model.number="analysisOptions.severityThreshold" label="Severity Threshold"
                      type="number" step="0.01" min="0" max="1" :disabled="processing" outlined
                      hint="Set a value between 0 and 1" persistent-hint></v-text-field>
                  </v-col>
                  <!-- language selection menu (only french or english) -->
                  <v-col cols="12" md="6">
                    <v-select v-model="analysisOptions.language"
                      :items="['afrikaans', 'albanian', 'amharic', 'arabic', 'armenian', 'assamese', 'azerbaijani', 'bashkir', 'basque', 'belarusian', 'bengali', 'bosnian', 'breton', 'bulgarian', 'cantonese', 'catalan', 'chinese', 'croatian', 'czech', 'danish', 'dutch', 'english', 'estonian', 'faroese', 'finnish', 'french', 'galician', 'georgian', 'german', 'greek', 'gujarati', 'haitian creole', 'hausa', 'hawaiian', 'hebrew', 'hindi', 'hungarian', 'icelandic', 'indonesian', 'italian', 'japanese', 'javanese', 'kannada', 'kazakh', 'khmer', 'korean', 'lao', 'latin', 'latvian', 'lingala', 'lithuanian', 'luxembourgish', 'macedonian', 'malagasy', 'malay', 'malayalam', 'maltese', 'maori', 'marathi', 'mongolian', 'myanmar', 'nepali', 'norwegian', 'nynorsk', 'occitan', 'pashto', 'persian', 'polish', 'portuguese', 'punjabi', 'romanian', 'russian', 'sanskrit', 'serbian', 'shona', 'sindhi', 'sinhala', 'slovak', 'slovenian', 'somali', 'spanish', 'sundanese', 'swahili', 'swedish', 'tagalog', 'tajik', 'tamil', 'tatar', 'telugu', 'thai', 'tibetan', 'turkish', 'turkmen', 'ukrainian', 'urdu', 'uzbek', 'vietnamese', 'welsh', 'yiddish', 'yoruba']"
                      label="Language" outlined :disabled="processing"></v-select>
                  </v-col>
                </v-row>

                <!-- Action Buttons -->
                <v-row class="mt-4">
                  <v-col>
                    <v-btn @click="inputType === 0 ? processAudioInput() : processYoutubeInput()" color="primary"
                      x-large block :loading="processing" :disabled="!canProcess">
                      <v-icon left>mdi-play</v-icon>
                      Analyze {{ inputType === 0 ? "Audio" : "Youtube Link" }}
                    </v-btn>
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <!-- Processing Status -->
        <v-row v-if="processing" justify="center" class="mt-6">
          <v-col cols="12" md="8">
            <v-card>
              <v-card-text class="text-center pa-6">
                <v-progress-circular indeterminate color="primary" size="64" class="mb-4"></v-progress-circular>
                <h3 class="text-h6 mb-2">{{ processingStatus }}</h3>
                <p class="text-body-2 grey--text">
                  This may take a few moments depending on the audio length
                </p>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <!-- Results Section -->
        <div v-if="analysisResults">
          <!-- Transcription -->
          <v-row justify="center" class="mt-6">
            <v-col cols="12" md="10">
              <v-card class="analysis-card">
                <v-card-title class="pa-5">
                  <v-icon left color="blue" class="mr-2">mdi-text</v-icon>
                  Transcription
                </v-card-title>
                <v-card-text class="text-wrap scrollable-text">
                  <p class="text-body-1">{{ analysisResults.text_analyzed }}</p>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>

          <!-- Analysis Results Grid -->
          <v-row class="mt-6">
            <!-- Logical Fallacies -->
            <v-col v-if="analysisResults.fallacies" cols="12" md="6">
              <v-card class="analysis-card h-100">
                <v-card-title class="red--text align-center pa-5">
                  <v-icon left color="red" class="mr-2">mdi-alert-circle</v-icon>
                  Logical Fallacies
                  <v-chip class=" ml-2" color="red" text-color="white" small>
                    {{ analysisResults.fallacies.length }}
                  </v-chip>
                </v-card-title>
                <v-card-text>
                  <div v-if="analysisResults.fallacies.length === 0">
                    <v-alert type="success" text>
                      No logical fallacies detected!
                    </v-alert>
                  </div>
                  <div v-else>
                    <v-chip v-for="fallacy in analysisResults.fallacies" :key="fallacy.type" class="fallacy-chip"
                      color="red" text-color="white" small :title="fallacy.description">
                      {{ fallacy.type }}
                    </v-chip>
                  </div>
                </v-card-text>
              </v-card>
            </v-col>

            <!-- Argument Structure Card -->
            <v-col v-if="analysisResults.argument_structure" cols="12" md="6">
              <v-card class="analysis-card h-100">
                <v-card-title class="pa-5">
                  <v-icon left color="indigo" class="mr-2">mdi-sitemap</v-icon>
                  Argument Structure
                </v-card-title>
                <v-card-text>
                  <v-list dense>
                    <v-list-item>
                      <v-list-item-content>
                        <v-list-item-title>
                          <strong>Type:</strong> {{ analysisResults.argument_structure.argument_type }}
                        </v-list-item-title>
                      </v-list-item-content>
                    </v-list-item>
                    <v-list-item>
                      <v-list-item-content>
                        <v-list-item-title>
                          <strong>Coherence:</strong> {{ analysisResults.argument_structure.coherence }}
                        </v-list-item-title>
                      </v-list-item-content>
                    </v-list-item>
                    <v-list-item>
                      <v-list-item-content>
                        <v-list-item-title>
                          <strong>Strength:</strong> {{ analysisResults.argument_structure.strength }}
                        </v-list-item-title>
                      </v-list-item-content>
                    </v-list-item>
                    <v-list-item>
                      <v-list-item-content>
                        <v-list-item-title>
                          <strong>Conclusion:</strong>
                          <span class="text-wrap">{{ analysisResults.argument_structure.conclusion }}</span>
                        </v-list-item-title>
                      </v-list-item-content>
                    </v-list-item>
                    <v-list-item>
                      <v-list-item-content>
                        <v-list-item-title>
                          <strong>Premises ({{ analysisResults.argument_structure.premises.length }}):</strong>
                        </v-list-item-title>
                        <v-list dense class="ml-4" style="max-height: 120px; overflow-y: auto;">
                          <v-list-item v-for="(premise, idx) in analysisResults.argument_structure.premises.slice(0, 5)"
                            :key="idx">
                            <v-list-item-content>
                              <v-list-item-title class="text-wrap">{{ premise }}</v-list-item-title>
                            </v-list-item-content>
                          </v-list-item>
                          <v-list-item v-if="analysisResults.argument_structure.premises.length > 5">
                            <v-list-item-content>
                              <v-list-item-title class="grey--text">...and {{
                                analysisResults.argument_structure.premises.length - 5 }} more</v-list-item-title>
                            </v-list-item-content>
                          </v-list-item>
                        </v-list>
                      </v-list-item-content>
                    </v-list-item>
                  </v-list>
                </v-card-text>
              </v-card>
            </v-col>

            <!-- Overall Quality Card -->
            <v-col v-if="analysisResults.overall_quality !== undefined" cols="12" md="6">
              <v-card class="analysis-card h-100">
                <v-card-title class="pa-5">
                  <v-icon left :color="overallQualityColor" class="mr-2">mdi-star-circle</v-icon>
                  Overall Quality
                </v-card-title>
                <v-card-text class="text-center">
                  <v-progress-circular :model-value="analysisResults.overall_quality * 100" :color="overallQualityColor"
                    size="70" width="8" class="mb-2">
                    {{ (analysisResults.overall_quality * 100).toFixed(0) }}%
                  </v-progress-circular>
                  <div>
                    <span :style="{ color: overallQualityColor, fontWeight: 'bold' }">
                      {{ overallQualityLabel }}
                    </span>
                  </div>
                </v-card-text>
              </v-card>
            </v-col>

            <!-- Argument Solidity -->
            <v-col v-if="analysisResults.solidity" cols="12" md="6">
              <v-card class="analysis-card h-100">
                <v-card-title>
                  <v-icon left color="purple">mdi-diamond-stone</v-icon>
                  Argument Solidity
                </v-card-title>
                <v-card-text>
                  <v-progress-linear :value="analysisResults.solidity.score * 10" color="purple" height="8"
                    class="mb-3"></v-progress-linear>
                  <p>
                    <strong>Rating:</strong> {{ analysisResults.solidity.rating }}
                  </p>
                  <p class="text-body-2">
                    {{ analysisResults.solidity.explanation }}
                  </p>
                </v-card-text>
              </v-card>
            </v-col>

            <!-- Key Claims -->
            <v-col v-if="analysisResults.claims" cols="12" md="6">
              <v-card class="analysis-card h-100">
                <v-card-title>
                  <v-icon left color="green">mdi-format-list-bulleted</v-icon>
                  Key Claims
                </v-card-title>
                <v-card-text>
                  <v-list dense>
                    <v-list-item v-for="(claim, index) in analysisResults.claims" :key="index">
                      <v-list-item-content>
                        <v-list-item-title class="text-wrap">
                          {{ claim }}
                        </v-list-item-title>
                      </v-list-item-content>
                    </v-list-item>
                  </v-list>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>

          <!-- Export Options -->
          <v-row justify="center" class="mt-6">
            <v-col cols="12" md="8">
              <v-card>
                <v-card-title class="pa-5">
                  <v-icon left class="mr-2">mdi-download</v-icon>
                  Export Results
                </v-card-title>
                <v-card-actions class="justify-center">
                  <v-btn @click="exportResults('json')" color="primary" outlined>
                    <v-icon left>mdi-code-json</v-icon>
                    Export as JSON
                  </v-btn>
                  <v-btn @click="exportResults('pdf')" color="secondary" outlined>
                    <v-icon left>mdi-file-pdf-box</v-icon>
                    Export as PDF
                  </v-btn>
                </v-card-actions>
              </v-card>
            </v-col>
          </v-row>
        </div>
      </v-container>
    </v-main>

    <!-- Footer -->
    <v-footer dark padless class="gradient-bg-footer">
      <v-container>
        <v-row justify="center">
          <v-col class="text-center">
            <p class="mb-0">
              &copy; 2025 Argument Analyzer - Powered by AI
            </p>
          </v-col>
        </v-row>
      </v-container>
    </v-footer>
  </v-app>
</template>

<script>
import WhisperApiClient from '@/api/whisperApiClient'; // Placeholder for Whisper API client
import jsPDF from 'jspdf';

export default {
  name: 'ArgumentAnalyzer',
  data() {
    return {
      inputType: 0,
      audioFile: null,
      youtubeUrl: '',
      processing: false,
      processingStatus: 'Initializing...',
      analysisOptions: {
        analyzeStructure: true,
        detectFallacies: true,
        evaluateCoherence: true,
        includeContext: true,
        severityThreshold: 0.5,
        language: 'english', // Default language
      },
      analysisResults: null,
      whisperApiClient: null,
      textToAnalyze: '',
      analyzeApiUrl: '',
      audioFilePath: '',
    }
  },
  mounted() {
    const USERNAME = import.meta.env.VITE_WHISPER_USERNAME;
    const PASSWORD = import.meta.env.VITE_WHISPER_PASSWORD;
    const HUGGING_FACE_API_KEY = import.meta.env.VITE_HUGGING_FACE_API_KEY;
    console.log('Initializing Whisper API client...');
    this.whisperApiClient = new WhisperApiClient(
      "https://whisper-webui.myia.io/",
      USERNAME,
      PASSWORD,
      HUGGING_FACE_API_KEY);
    this.analyzeApiUrl = import.meta.env.VITE_ANALYZE_API_URL || 'http://localhost:5000/api';
    this.audioFilePath = import.meta.env.VITE_FILE_UPLOAD_DIR || '/tmp/uploads';
  },
  computed: {
    canProcess() {
      if (this.inputType === 0) {
        return this.audioFile !== null;
      } else {
        return this.youtubeUrl.trim() !== '' && this.isValidYouTubeUrl(this.youtubeUrl);
      }
    },
    overallQualityColor() {
      const q = this.analysisResults?.overall_quality;
      if (q >= 0.8) return 'green';
      if (q >= 0.5) return 'orange';
      return 'red';
    },
    overallQualityLabel() {
      const q = this.analysisResults?.overall_quality;
      if (q >= 0.8) return 'Excellent';
      if (q >= 0.5) return 'Average';
      return 'Poor';
    },
  },
  methods: {
    urlValidation(value) {
      if (!value) return true;
      return this.isValidYouTubeUrl(value) || 'Please enter a valid YouTube URL';
    },
    isValidYouTubeUrl(url) {
      const pattern = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+/;
      return pattern.test(url);
    },
    async processAudioInput() {
      this.processing = true;
      this.analysisResults = null;
      try {
        // Add file type validation
        if (!(this.audioFile instanceof File)) {
          throw new Error('Invalid file object');
        }

        console.log("Processing file:", this.audioFile.name);

        // Uncomment to debug Gradio interface
        // await this.whisperApiClient.debugGradioInterface();
        const results = await this.whisperApiClient.transcribeFileTest(this.audioFile);
        // const results = await this.rawTranscribe(
        //   this.audioFile
        // );
        if (results?.transcription) {
          this.textToAnalyze = results.transcription;
          await this.generateResults();
        }
      } catch (error) {
        console.error('Processing error:', error);
        this.processingStatus = `Error: ${error.message}`;
      } finally {
        this.processing = false;
        this.processingStatus = 'Initializing...';
      }
    },
    // Test method for direct API call
    async rawTranscribe(file) {
      try {
        // Create basic auth header
        const auth = btoa(`${this.username}:${this.password}`);

        // Create form data
        const formData = new FormData();
        formData.append('file', file);

        // Make direct request
        const response = await fetch(`${this.analyzeApiUrl}/transcribe_file`, {
          method: 'POST',
          headers: {
            'Authorization': `Basic ${auth}`,
            'Access-Control-Allow-Origin': '*'
          },
          body: formData
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
      } catch (error) {
        console.error('RAW request error:', error);
        throw error;
      }
    },
    async processYoutubeInput() {
      this.processing = true;
      this.analysisResults = null;
      try {
        const results = await this.whisperApiClient.transcribeYouTube(this.youtubeUrl, { "param_4": this.analysisOptions.language });

        if (results) {
          this.textToAnalyze = results.raw.data[0];
          this.processingStatus = 'Analyzing arguments and detecting fallacies...';
          await this.generateResults();
        } else {
          console.error('No transcription text found');
          this.processingStatus = 'Error: No transcription text found';
        }
      } catch (error) {
        console.error('Processing error:', error);
      } finally {
        this.processing = false;
        this.processingStatus = 'Initializing...';
      }
    },
    async generateResults() {
      const analysisParameters = {
        "options": {
          "analyze_structure": this.analysisOptions.analyzeStructure,
          "detect_fallacies": this.analysisOptions.detectFallacies,
          "evaluate_coherence": this.analysisOptions.evaluateCoherence,
          "include_context": this.analysisOptions.includeContext,
          "severity_threshold": this.analysisOptions.severityThreshold,
          "language": this.analysisOptions.language
        },
        "text": this.textToAnalyze
      };
      // Make the API call to analyze the text
      try {
        this.processingStatus = 'Analyzing arguments...';
        const response = await fetch(`${this.analyzeApiUrl}/analyze`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(analysisParameters)
        });
        if (!response.ok) {
          throw new Error('API request failed');
        }
        this.analysisResults = await response.json();
        // Remove the first two sentences from the transcription
        if (this.analysisResults.text_analyzed) {
          // Split by sentence-ending punctuation followed by a space or line break
          const sentences = this.analysisResults.text_analyzed.match(/[^.!?]+[.!?]+[\s\n]*/g);
          if (sentences && sentences.length > 2) {
            this.analysisResults.text_analyzed = sentences.slice(2).join('').trim();
          }
        }
        this.processingStatus = 'Analysis complete';
      } catch (error) {
        console.error('API call error:', error);
        return null;
      }

    },
    exportResults(format) {
      if (format === 'json') {
        const dataStr = JSON.stringify(this.analysisResults, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        this.downloadFile(dataBlob, 'analysis-results.json');
      } else if (format === 'pdf') {
        const doc = new jsPDF();
        let y = 15;
        const pageHeight = doc.internal.pageSize.getHeight();
        const marginBottom = 20;

        // Helper to check for page break
        function checkPageBreak(lines = 1) {
          if (y + lines * 6 > pageHeight - marginBottom) {
            doc.addPage();
            y = 15;
          }
        }

        // Title
        doc.setFontSize(18);
        doc.text('Argument Analysis Results', 10, y);
        y += 10;

        // Transcription
        doc.setFontSize(14);
        checkPageBreak();
        doc.text('Transcription:', 10, y);
        y += 8;
        doc.setFontSize(11);
        const transcription = this.analysisResults.text_analyzed || '';
        const transLines = doc.splitTextToSize(transcription, 180);
        transLines.forEach(line => {
          checkPageBreak();
          doc.text(line, 10, y);
          y += 6;
        });

        // Logical Fallacies
        if (this.analysisResults.fallacies) {
          doc.setFontSize(14);
          checkPageBreak();
          doc.text('Logical Fallacies:', 10, y);
          y += 8;
          doc.setFontSize(11);
          if (this.analysisResults.fallacies.length === 0) {
            checkPageBreak();
            doc.text('- None detected', 12, y);
            y += 6;
          } else {
            this.analysisResults.fallacies.forEach(fallacy => {
              checkPageBreak();
              doc.text(`- ${fallacy.type}: ${fallacy.description || ''}`, 12, y);
              y += 6;
            });
          }
          y += 2;
        }

        // Argument Structure
        if (this.analysisResults.argument_structure) {
          doc.setFontSize(14);
          checkPageBreak();
          doc.text('Argument Structure:', 10, y);
          y += 8;
          doc.setFontSize(11);
          const arg = this.analysisResults.argument_structure;
          [
            `Type: ${arg.argument_type}`,
            `Coherence: ${arg.coherence}`,
            `Strength: ${arg.strength}`,
            'Conclusion:'
          ].forEach(text => {
            checkPageBreak();
            doc.text(text, 12, y);
            y += 6;
          });
          const conclLines = doc.splitTextToSize(arg.conclusion || '', 170);
          conclLines.forEach(line => {
            checkPageBreak();
            doc.text(line, 16, y);
            y += 6;
          });
          checkPageBreak();
          doc.text(`Premises (${arg.premises.length}):`, 12, y);
          y += 6;
          arg.premises.slice(0, 5).forEach((premise, idx) => {
            const premiseLines = doc.splitTextToSize(`- ${premise}`, 170);
            premiseLines.forEach(line => {
              checkPageBreak();
              doc.text(line, 16, y);
              y += 6;
            });
          });
          if (arg.premises.length > 5) {
            checkPageBreak();
            doc.text(`...and ${arg.premises.length - 5} more`, 16, y);
            y += 6;
          }
          y += 2;
        }

        // Overall Quality
        if (this.analysisResults.overall_quality !== undefined) {
          doc.setFontSize(14);
          checkPageBreak();
          doc.text('Overall Quality:', 10, y);
          y += 8;
          doc.setFontSize(11);
          checkPageBreak();
          doc.text(
            `${(this.analysisResults.overall_quality * 100).toFixed(1)}% (${this.overallQualityLabel})`,
            12, y
          );
          y += 10;
        }

        // Solidity
        if (this.analysisResults.solidity) {
          doc.setFontSize(14);
          checkPageBreak();
          doc.text('Argument Solidity:', 10, y);
          y += 8;
          doc.setFontSize(11);
          checkPageBreak();
          doc.text(`Rating: ${this.analysisResults.solidity.rating}`, 12, y);
          y += 6;
          const explLines = doc.splitTextToSize(this.analysisResults.solidity.explanation || '', 170);
          explLines.forEach(line => {
            checkPageBreak();
            doc.text(line, 12, y);
            y += 6;
          });
          y += 2;
        }

        // Key Claims
        if (this.analysisResults.claims) {
          doc.setFontSize(14);
          checkPageBreak();
          doc.text('Key Claims:', 10, y);
          y += 8;
          doc.setFontSize(11);
          this.analysisResults.claims.forEach((claim, idx) => {
            const claimLines = doc.splitTextToSize(`- ${claim}`, 170);
            claimLines.forEach(line => {
              checkPageBreak();
              doc.text(line, 12, y);
              y += 6;
            });
          });
        }

        doc.save('analysis-results.pdf');
      }
    },
    downloadFile(blob, filename) {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    }
  }
}
</script>

<style scoped>
.gradient-bg {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.gradient-bg-footer {
  background: linear-gradient(180deg, #121212 0%, #212138 100%);
}

.card-shadow {
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1) !important;
}

.analysis-card {
  transition: transform 0.2s ease-in-out;
}

.analysis-card:hover {
  transform: translateY(-2px);
}

.fallacy-chip {
  margin: 2px;
}

.loading-overlay {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(4px);
}

.scrollable-text {
  max-height: 300px;
  overflow-y: auto;
}
</style>