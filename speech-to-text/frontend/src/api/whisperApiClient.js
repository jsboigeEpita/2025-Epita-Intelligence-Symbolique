/**
 * Whisper WebUI API Client using @gradio/client
 * For the doc and test the UI: https://whisper-webui.myia.io/?view=api
 * 
 * Installation: npm install @gradio/client
 */

import { Client, handle_file } from "@gradio/client";

class WhisperApiClient {
  constructor(baseUrl = "https://whisper-webui.myia.io/", username, password, apiKey) {
    this.baseUrl = baseUrl;
    this.username = username;
    this.password = password;
    this.apiKey = apiKey;
    this.client = null;
  }

  async connect() {
    if (!this.client) {
      console.log('Credentials:', this.username, this.password, this.apiKey);
      this.client = await Client.connect(this.baseUrl, {
        auth: [this.username, this.password]
      });
    }
    return this.client;
  }

  async transcribeYouTube(youtubeLink, options = {}) {
    const defaultOptions = {
      file_format: "txt",
      add_timestamp: false,
      progress: "large-v3-turbo", // model
      param_4: "english", // language
      param_5: false, // use_auth_token
      param_6: 5, // chunk_length
      param_7: -1, // stride_length_s
      param_8: 0.6, // max_new_tokens
      param_9: "float16", // dtype
      param_10: 5, // batch_size
      param_11: 1, // assistant_model
      param_12: true, // use_bettertransformer
      param_13: 0.5, // flash_attention_2
      param_14: "Hello!!", // preprocess_text
      param_15: 0, // postprocess_text
      param_16: 2.4, // temperature
      param_17: 1, // compression_ratio_threshold
      param_18: 1, // log_prob_threshold
      param_19: 0, // no_speech_threshold
      param_20: "Hello!!", // initial_prompt
      param_21: true, // suppress_tokens
      param_22: "[-1]", // suppress_numerals
      param_23: 1, // max_initial_timestamp
      param_24: false, // word_timestamps
      param_25: "'\"¿([{-", // prepend_punctuations
      param_26: "'.。,，!！?？:：\")]}、", // append_punctuations
      param_27: 3, // max_line_width
      param_28: 30, // max_line_count
      param_29: 3, // max_words_per_line
      param_30: "Hello!!", // highlight_words
      param_31: 0.5, // segment_resolution
      param_32: 1, // fonts_size
      param_33: 24, // fonts_color
      param_34: true, // karaoke
      param_35: false, // embed_subs
      param_36: 0.5, // similarity_threshold
      param_37: 250, // min_word_dur
      param_38: 9999, // only_voice_freq
      param_39: 1000, // min_words_per_segment
      param_40: 2000, // min_words_per_segment_threshold
      param_41: false, // time_sync_adjustment
      param_42: "cuda", // device
      param_43: this.apiKey, // hugging_face_token
      param_44: true, // use_cache
      param_45: false, // delete_cache
      param_46: "UVR-MDX-NET-Inst_HQ_4", // uvr_model
      param_47: "cuda", // uvr_device
      param_48: 256, // uvr_segment_size
      param_49: false, // uvr_save_file
      param_50: true // bgm_separation
    };

    const finalOptions = { ...defaultOptions, ...options };

    try {
      const client = await this.connect();

      const result = await client.predict("/transcribe_youtube", {
        youtube_link: youtubeLink,
        file_format: finalOptions.file_format,
        add_timestamp: finalOptions.add_timestamp,
        progress: finalOptions.progress,
        param_4: finalOptions.param_4,
        param_5: finalOptions.param_5,
        param_6: finalOptions.param_6,
        param_7: finalOptions.param_7,
        param_8: finalOptions.param_8,
        param_9: finalOptions.param_9,
        param_10: finalOptions.param_10,
        param_11: finalOptions.param_11,
        param_12: finalOptions.param_12,
        param_13: finalOptions.param_13,
        param_14: finalOptions.param_14,
        param_15: finalOptions.param_15,
        param_16: finalOptions.param_16,
        param_17: finalOptions.param_17,
        param_18: finalOptions.param_18,
        param_19: finalOptions.param_19,
        param_20: finalOptions.param_20,
        param_21: finalOptions.param_21,
        param_22: finalOptions.param_22,
        param_23: finalOptions.param_23,
        param_24: finalOptions.param_24,
        param_25: finalOptions.param_25,
        param_26: finalOptions.param_26,
        param_27: finalOptions.param_27,
        param_28: finalOptions.param_28,
        param_29: finalOptions.param_29,
        param_30: finalOptions.param_30,
        param_31: finalOptions.param_31,
        param_32: finalOptions.param_32,
        param_33: finalOptions.param_33,
        param_34: finalOptions.param_34,
        param_35: finalOptions.param_35,
        param_36: finalOptions.param_36,
        param_37: finalOptions.param_37,
        param_38: finalOptions.param_38,
        param_39: finalOptions.param_39,
        param_40: finalOptions.param_40,
        param_41: finalOptions.param_41,
        param_42: finalOptions.param_42,
        param_43: finalOptions.param_43,
        param_44: finalOptions.param_44,
        param_45: finalOptions.param_45,
        param_46: finalOptions.param_46,
        param_47: finalOptions.param_47,
        param_48: finalOptions.param_48,
        param_49: finalOptions.param_49,
        param_50: finalOptions.param_50
      });

      return this.processResult(result);
    } catch (error) {
      console.error('Error calling Whisper API:', error);
      throw error;
    }
  }
  /**
  /* Transcribe a file (e.g., audio file)
  */

  async transcribeFileTest(file, options = {}) {
    // Use Gradio's handle_file function directly
    // const fileRef = handle_file(file);
    const fileRef = {
      meta: { _type: 'gradio.FileData' },
      orig_name: file.name,
      path: URL.createObjectURL(file),
      url: URL.createObjectURL(file)
    };
    console.log('File reference:', fileRef);

    // const defaultOptions = {
    //   files: [fileRef],
    //   input_folder_path: "",
    //   include_subdirectory: false,
    //   save_same_dir: true,
    //   file_format: "txt",
    //   add_timestamp: true,
    //   progress: "tiny.en",
    //   param_7: "afrikaans",
    //   param_8: true,
    //   param_9: 0,
    //   param_10: 0,
    //   param_11: 0,
    //   param_12: "int8",
    //   param_13: 0,
    //   param_14: 0,
    //   param_15: true,
    //   param_16: 0,
    //   param_17: "",
    //   param_18: 0,
    //   param_19: 0,
    //   param_20: 0,
    //   param_21: 0,
    //   param_22: 0,
    //   param_23: "",
    //   param_24: true,
    //   param_25: "",
    //   param_26: 0,
    //   param_27: true,
    //   param_28: "",
    //   param_29: "",
    //   param_30: 0,
    //   param_31: 0,
    //   param_32: 0,
    //   param_33: "",
    //   param_34: 0,
    //   param_35: 0,
    //   param_36: 0,
    //   param_37: true,
    //   param_38: true,
    //   param_39: 0,
    //   param_40: 0,
    //   param_41: 0,
    //   param_42: 0,
    //   param_43: 0,
    //   param_44: true,
    //   param_45: "cpu",
    //   param_46: "",
    //   param_47: true,
    //   param_48: true,
    //   param_49: "UVR-MDX-NET-Inst_HQ_4",
    //   param_50: "cpu",
    //   param_51: 0,
    //   param_52: true,
    //   param_53: true,
    // };

    // const finalOptions = { ...defaultOptions, ...options };

    const payload = {
      files: [fileRef], // Must be an array
      file_format: "txt", // Output format
      // progress: "base", // Use the simplest model possible
      // param_4: "english", // Auto-detect language
    };

    try {
      const client = await this.connect();
      const result = await client.predict("/transcribe_file", payload);
      URL.revokeObjectURL(fileRef.path);
      URL.revokeObjectURL(fileRef.url);
      return this.processResult(result);
    } catch (error) {
      console.error('Error in transcribeFileTest:', error);
      throw new Error(`Transcription failed: ${error.message}`);
    }
  }


  // Add this debugging method to your WhisperApiClient class
  async debugGradioInterface() {
    try {
      const client = await this.connect();
      console.log('Gradio client connected successfully');

      // Get the interface info to understand expected parameters
      const interfaceInfo = await client.view_api();
      console.log('Gradio interface info:', interfaceInfo);

      // Look for the transcribe_file endpoint specifically
      const transcribeEndpoint = interfaceInfo.named_endpoints['/transcribe_file'];
      if (transcribeEndpoint) {
        console.log('Transcribe endpoint details:', transcribeEndpoint);
        console.log('Expected parameters:', transcribeEndpoint.parameters);
        console.log('Expected returns:', transcribeEndpoint.returns);
      }

      return interfaceInfo;
    } catch (error) {
      console.error('Error getting Gradio interface info:', error);
      throw error;
    }
  }

  processResult(result) {
    if (result && result.data && result.data[0]) {
      const transcription = result.data[0];
      const lines = transcription.split('\n').filter(line => line.trim() !== '');

      return {
        success: true,
        transcription: transcription,
        lines: lines,
        raw: result
      };
    }

    return {
      success: false,
      error: 'No transcription data received',
      raw: result
    };
  }

  async disconnect() {
    if (this.client) {
      await this.client.close();
      this.client = null;
    }
  }
}

export default WhisperApiClient;

// Usage example
async function testWhisperAPI() {
  // Environment variables (you'll need to set these)
  const USERNAME = process.env.WHISPER_USERNAME || 'your_username';
  const PASSWORD = process.env.WHISPER_PASSWORD || 'your_password';
  const HUGGING_FACE_API_KEY = process.env.HUGGING_FACE_API_KEY || 'your_api_key';

  console.log('Credentials:', USERNAME, PASSWORD, HUGGING_FACE_API_KEY);

  const client = new WhisperApiClient(
    "https://whisper-webui.myia.io/",
    USERNAME,
    PASSWORD,
    HUGGING_FACE_API_KEY
  );

  try {
    // Test YouTube transcription
    const result = await client.transcribeYouTube(
      "https://www.youtube.com/watch?v=n9Gj5QCSsBk", // Example with Trump speech
      {
        file_format: "txt",
        add_timestamp: false,
        progress: "large-v3-turbo",
        param_4: "english"
      }
    );

    console.log('Transcription Result:', result);

    if (result.success) {
      console.log('\nFormatted transcription:');
      result.lines.forEach(line => {
        console.log(line);
      });
    } else {
      console.error('Transcription failed:', result.error);
    }

    // Test file transcription (example)
    /*
    const fileInput = document.getElementById('audio-file');
    if (fileInput && fileInput.files[0]) {
      const fileResult = await client.transcribeFile(fileInput.files[0], {
        file_format: "SRT",
        add_timestamp: true,
        progress: "tiny.en",
        param_7: "english"
      });
      
      console.log('File transcription result:', fileResult);
    }
    */

  } catch (error) {
    console.error('Error:', error);
  } finally {
    await client.disconnect();
  }
}

// For Node.js environment
if (typeof module !== 'undefined' && module.exports) {
  module.exports = WhisperApiClient;

  // Run test if this file is executed directly
  if (require.main === module) {
    testWhisperAPI();
  }
}

// For browser environment
if (typeof window !== 'undefined') {
  window.WhisperApiClient = WhisperApiClient;
}

// Example usage in Vue component:
/*
// First install: npm install @gradio/client

// In your Vue component methods:
async processInput() {
  this.processing = true;
  this.processingStatus = 'Converting audio to text...';
  
  try {
    const client = new WhisperApiClient(
      "https://whisper-webui.myia.io/",
      process.env.VUE_APP_WHISPER_USERNAME,
      process.env.VUE_APP_WHISPER_PASSWORD,
      process.env.VUE_APP_HUGGING_FACE_API_KEY
    );

    let result;
    if (this.inputType === 0) {
      // Audio file
      result = await client.transcribeFile(this.audioFile, {
        file_format: "txt",
        add_timestamp: false,
        progress: "large-v3-turbo",
        param_7: "english"
      });
    } else {
      // YouTube URL
      result = await client.transcribeYouTube(this.youtubeUrl, {
        file_format: "txt",
        add_timestamp: false,
        progress: "large-v3-turbo",
        param_4: "english"
      });
    }
    
    if (result.success) {
      // Now call your argument analysis API with result.transcription
      this.processingStatus = 'Analyzing arguments...';
      // ... rest of your analysis logic
      this.analysisResults = {
        transcription: result.transcription,
        // ... other analysis results
      };
    } else {
      throw new Error(result.error);
    }
    
    await client.disconnect();
  } catch (error) {
    console.error('Error:', error);
    // Handle error in UI
  } finally {
    this.processing = false;
  }
}
*/