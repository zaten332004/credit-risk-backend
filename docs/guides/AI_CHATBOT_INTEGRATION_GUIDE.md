# 🔗 Gemini AI Chatbot Integration Guide

## 📱 Multi-Platform Integration

### 1️⃣ Flutter Mobile App

#### Setup Dependencies

```yaml
# pubspec.yaml
dependencies:
  flutter:
    sdk: flutter
  http: ^1.1.0
  provider: ^6.0.0
  dio: ^5.3.0
  jwt_decoder: ^2.0.1
```

#### Authentication Service

```dart
class AuthService {
  final String _baseUrl = 'http://your-backend:8000/api/v1';
  String? _token;
  
  Future<String> login(String username, String password) async {
    final response = await http.post(
      Uri.parse('$_baseUrl/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'username': username,
        'password': password,
      }),
    );
    
    if (response.statusCode == 200) {
      _token = jsonDecode(response.body)['access_token'];
      return _token!;
    }
    throw Exception('Login failed');
  }
  
  String? get token => _token;
}
```

#### Chat Service

```dart
class ChatService {
  final String _baseUrl = 'http://your-backend:8000/api/v1/ai-chat';
  final AuthService _auth;
  
  ChatService(this._auth);
  
  Future<StartChatResponse> startChat({
    required String sessionName,
    String? initialContext,
  }) async {
    final response = await http.post(
      Uri.parse('$_baseUrl/start'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ${_auth.token}',
      },
      body: jsonEncode({
        'session_name': sessionName,
        'initial_context': initialContext,
      }),
    );
    
    if (response.statusCode == 200) {
      return StartChatResponse.fromJson(
        jsonDecode(response.body),
      );
    }
    throw Exception('Failed to start chat');
  }
  
  Future<SendMessageResponse> sendMessage({
    required int sessionId,
    required String message,
    Map<String, dynamic>? customerContext,
  }) async {
    final response = await http.post(
      Uri.parse('$_baseUrl/send'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ${_auth.token}',
      },
      body: jsonEncode({
        'session_id': sessionId,
        'message': message,
        'customer_context': customerContext,
      }),
    );
    
    if (response.statusCode == 200) {
      return SendMessageResponse.fromJson(
        jsonDecode(response.body),
      );
    }
    throw Exception('Failed to send message');
  }
  
  Future<List<ChatMessage>> getChatHistory({
    required int sessionId,
    int limit = 50,
  }) async {
    final response = await http.get(
      Uri.parse('$_baseUrl/history/$sessionId?limit=$limit'),
      headers: {
        'Authorization': 'Bearer ${_auth.token}',
      },
    );
    
    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((m) => ChatMessage.fromJson(m)).toList();
    }
    throw Exception('Failed to get chat history');
  }
}
```

#### UI Widget

```dart
class ChatScreen extends StatefulWidget {
  final int sessionId;
  
  const ChatScreen({required this.sessionId});
  
  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  late ChatService _chatService;
  final TextEditingController _messageController = TextEditingController();
  List<ChatMessage> _messages = [];
  
  @override
  void initState() {
    super.initState();
    _chatService = Provider.of<ChatService>(context, listen: false);
    _loadHistory();
  }
  
  Future<void> _loadHistory() async {
    try {
      final messages = await _chatService.getChatHistory(
        sessionId: widget.sessionId,
      );
      setState(() {
        _messages = messages;
      });
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e')),
      );
    }
  }
  
  Future<void> _sendMessage() async {
    final text = _messageController.text.trim();
    if (text.isEmpty) return;
    
    try {
      final response = await _chatService.sendMessage(
        sessionId: widget.sessionId,
        message: text,
      );
      
      setState(() {
        _messages.add(ChatMessage(
          role: 'user',
          content: text,
          timestamp: DateTime.now(),
        ));
        _messages.add(ChatMessage(
          role: 'assistant',
          content: response.message,
          timestamp: DateTime.now(),
        ));
      });
      
      _messageController.clear();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e')),
      );
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Financial Risk Analysis')),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              itemCount: _messages.length,
              itemBuilder: (context, index) {
                final msg = _messages[index];
                final isUser = msg.role == 'user';
                
                return Align(
                  alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    margin: const EdgeInsets.all(8),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: isUser ? Colors.blue : Colors.grey[300],
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      msg.content,
                      style: TextStyle(
                        color: isUser ? Colors.white : Colors.black,
                      ),
                    ),
                  ),
                );
              },
            ),
          ),
          Container(
            padding: const EdgeInsets.all(8),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _messageController,
                    decoration: InputDecoration(
                      hintText: 'Nhập câu hỏi...',
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                IconButton(
                  onPressed: _sendMessage,
                  icon: const Icon(Icons.send),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
```

---

### 2️⃣ React Web App

#### Setup

```bash
npm install axios react-query zustand
```

#### API Client

```typescript
// api/chatApi.ts
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api/v1/ai-chat';

const chatApi = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
chatApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const startChat = (sessionName: string, initialContext?: string) =>
  chatApi.post('/start', { session_name: sessionName, initial_context: initialContext });

export const sendMessage = (sessionId: number, message: string, customerContext?: any) =>
  chatApi.post('/send', { session_id: sessionId, message, customer_context: customerContext });

export const getChatHistory = (sessionId: number, limit = 50) =>
  chatApi.get(`/history/${sessionId}?limit=${limit}`);

export const closeChat = (sessionId: number) =>
  chatApi.post(`/close/${sessionId}`);

export const getSessions = () => chatApi.get('/sessions');

export const getReport = (sessionId: number) => chatApi.get(`/report/${sessionId}`);
```

#### Custom Hook

```typescript
// hooks/useChat.ts
import { useState } from 'react';
import * as chatApi from '../api/chatApi';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export const useChat = (sessionId: number) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const loadHistory = async () => {
    try {
      setLoading(true);
      const { data } = await chatApi.getChatHistory(sessionId);
      setMessages(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };
  
  const sendMessage = async (text: string) => {
    try {
      const { data } = await chatApi.sendMessage(sessionId, text);
      
      setMessages((prev) => [
        ...prev,
        { role: 'user', content: text, timestamp: new Date().toISOString() },
        { role: 'assistant', content: data.message, timestamp: data.timestamp },
      ]);
    } catch (err) {
      setError((err as Error).message);
    }
  };
  
  return { messages, loading, error, loadHistory, sendMessage };
};
```

#### Chat Component

```tsx
// components/ChatBox.tsx
import React, { useEffect, useState } from 'react';
import { useChat } from '../hooks/useChat';

interface ChatBoxProps {
  sessionId: number;
}

export const ChatBox: React.FC<ChatBoxProps> = ({ sessionId }) => {
  const { messages, loading, error, loadHistory, sendMessage } = useChat(sessionId);
  const [input, setInput] = useState('');
  
  useEffect(() => {
    loadHistory();
  }, [sessionId]);
  
  const handleSend = async () => {
    if (input.trim()) {
      await sendMessage(input);
      setInput('');
    }
  };
  
  return (
    <div className="chat-container">
      <div className="messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <span className="role">{msg.role === 'user' ? '👤' : '🤖'}</span>
            <span className="content">{msg.content}</span>
          </div>
        ))}
      </div>
      
      {error && <div className="error">{error}</div>}
      
      <div className="input-area">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Nhập câu hỏi..."
        />
        <button onClick={handleSend} disabled={loading}>
          {loading ? 'Đang gửi...' : 'Gửi'}
        </button>
      </div>
    </div>
  );
};
```

#### CSS Styling

```css
/* styles/chat.css */
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  border: 1px solid #ccc;
  border-radius: 8px;
  overflow: hidden;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: #f5f5f5;
}

.message {
  margin-bottom: 12px;
  display: flex;
  gap: 8px;
}

.message.user {
  justify-content: flex-end;
}

.message.assistant {
  justify-content: flex-start;
}

.message .role {
  font-size: 20px;
}

.message .content {
  padding: 8px 12px;
  border-radius: 8px;
  max-width: 70%;
  word-wrap: break-word;
}

.message.user .content {
  background: #007bff;
  color: white;
}

.message.assistant .content {
  background: #e9ecef;
  color: #333;
}

.input-area {
  display: flex;
  gap: 8px;
  padding: 16px;
  border-top: 1px solid #ccc;
}

.input-area input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
}

.input-area button {
  padding: 8px 16px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.input-area button:disabled {
  background: #ccc;
}

.error {
  color: #dc3545;
  padding: 8px;
  background: #f8d7da;
  border: 1px solid #f5c6cb;
  border-radius: 4px;
}
```

---

### 3️⃣ PowerBI Integration

#### Setup Power Query M

```m
// Get Chat Sessions
let
    Source = Json.Document(
        Web.Contents(
            "http://localhost:8000/api/v1/ai-chat/sessions",
            [Headers = [Authorization = "Bearer " & Token]]
        )
    )
in
    Source

// Get Chat History (Custom Function)
(sessionId as number) =>
let
    Source = Json.Document(
        Web.Contents(
            "http://localhost:8000/api/v1/ai-chat/history/" & Text.From(sessionId),
            [Headers = [Authorization = "Bearer " & Token]]
        )
    ),
    ConvertToTable = Table.FromList(Source, Splitter.SplitByNothing(), null, null, ExtraValues.Error),
    ExpandedRecords = Table.ExpandRecordColumn(ConvertedToTable, "Column1", {"role", "content", "timestamp"}, {"role", "content", "timestamp"})
in
    ExpandedRecords
```

#### PowerBI Dashboard Model

```dax
// Measures

Total Messages := COUNTA(ChatHistory[content])

User Messages := CALCULATE(
    COUNTA(ChatHistory[content]),
    ChatHistory[role] = "user"
)

Assistant Messages := CALCULATE(
    COUNTA(ChatHistory[content]),
    ChatHistory[role] = "assistant"
)

Active Sessions := CALCULATE(
    DISTINCTCOUNT(ChatSession[session_id]),
    ChatSession[is_active] = TRUE()
)

Avg Messages per Session := DIVIDE(
    [Total Messages],
    DISTINCTCOUNT(ChatSession[session_id])
)

Latest Session := MAXX(
    ALLSELECTED(ChatSession),
    ChatSession[created_at]
)
```

#### Dashboard Visualizations

- **Chat Volume**: Line chart (messages over time)
- **User vs Assistant**: Stacked bar chart
- **Active Sessions**: Card visual
- **Top Queries**: Word cloud (from user messages)
- **Session Duration**: Average/median scatter plot
- **Response Quality**: User satisfaction (if tracked)

---

### 4️⃣ Langflow Integration

#### Node Definition (YAML)

```yaml
name: Gemini Chat Node
description: Send message to financial risk analysis chatbot

inputs:
  - name: session_id
    type: integer
    required: true
    description: Chat session ID
    
  - name: message
    type: string
    required: true
    description: User message
    
  - name: customer_context
    type: object
    required: false
    description: Customer data for context
    
  - name: api_key
    type: credential
    required: true
    description: API authentication token

outputs:
  - name: response
    type: string
    description: AI response from Gemini
    
  - name: timestamp
    type: string
    description: Response timestamp

implementation: |
  import requests
  import json
  
  def run(session_id, message, customer_context, api_key):
      url = "http://localhost:8000/api/v1/ai-chat/send"
      headers = {
          "Authorization": f"Bearer {api_key}",
          "Content-Type": "application/json"
      }
      
      payload = {
          "session_id": session_id,
          "message": message,
          "customer_context": customer_context
      }
      
      response = requests.post(url, json=payload, headers=headers)
      
      if response.status_code == 200:
          data = response.json()
          return {
              "response": data["message"],
              "timestamp": data["timestamp"]
          }
      else:
          raise Exception(f"API Error: {response.text}")
```

#### Langflow Flow Configuration

```json
{
  "name": "Financial Risk Analysis Flow",
  "description": "Interactive financial risk assessment with Gemini AI",
  "nodes": [
    {
      "id": "input",
      "type": "input",
      "position": { "x": 0, "y": 0 },
      "data": {
        "label": "Customer Data",
        "customer_id": "number",
        "credit_score": "number",
        "annual_income": "number"
      }
    },
    {
      "id": "start_session",
      "type": "api",
      "position": { "x": 200, "y": 0 },
      "data": {
        "label": "Start Chat Session",
        "method": "POST",
        "url": "http://localhost:8000/api/v1/ai-chat/start"
      }
    },
    {
      "id": "send_message",
      "type": "gemini_chat",
      "position": { "x": 400, "y": 0 },
      "data": {
        "label": "Get AI Response",
        "model": "gemini-2.0-flash"
      }
    },
    {
      "id": "output",
      "type": "output",
      "position": { "x": 600, "y": 0 },
      "data": {
        "label": "Risk Analysis Report"
      }
    }
  ],
  "edges": [
    { "source": "input", "target": "start_session" },
    { "source": "start_session", "target": "send_message" },
    { "source": "send_message", "target": "output" }
  ]
}
```

---

### 5️⃣ AWS Lambda Deployment

#### Lambda Function Handler

```python
# lambda_function.py
import json
import boto3
import requests
from datetime import datetime

def lambda_handler(event, context):
    """
    Handle API Gateway requests and forward to chat service
    """
    
    try:
        # Parse request
        path = event.get('path', '')
        method = event.get('httpMethod', '')
        body = json.loads(event.get('body', '{}'))
        headers = event.get('headers', {})
        
        # Get authorization token
        auth = headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return error_response(401, 'Unauthorized')
        
        token = auth.replace('Bearer ', '')
        
        # Forward to backend
        backend_url = 'http://credit-risk-backend.example.com'
        response = requests.request(
            method=method,
            url=f'{backend_url}{path}',
            json=body,
            headers={'Authorization': auth}
        )
        
        return {
            'statusCode': response.status_code,
            'body': response.text,
            'headers': {'Content-Type': 'application/json'}
        }
        
    except Exception as e:
        return error_response(500, str(e))

def error_response(status, message):
    return {
        'statusCode': status,
        'body': json.dumps({'error': message}),
        'headers': {'Content-Type': 'application/json'}
    }
```

#### SAM Template

```yaml
# template.yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Globals:
  Function:
    Timeout: 30
    Runtime: python3.11
    Environment:
      Variables:
        GEMINI_API_KEY: !Ref GeminiApiKey
        BACKEND_URL: !Ref BackendUrl

Parameters:
  GeminiApiKey:
    Type: String
    NoEcho: true
  BackendUrl:
    Type: String
    Default: http://localhost:8000

Resources:
  ChatFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: .
      Handler: lambda_function.lambda_handler
      Events:
        ChatAPI:
          Type: Api
          Properties:
            RestApiId: !Ref ChatAPI
            Path: /ai-chat/{proxy+}
            Method: ANY

  ChatAPI:
    Type: AWS::Serverless::Api
    Properties:
      StageName: prod
      Auth:
        DefaultAuthorizer: TokenAuthorizer
        Authorizers:
          TokenAuthorizer:
            FunctionArn: !GetAtt AuthorizerFunction.Arn

  AuthorizerFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: authorizer/
      Handler: authorizer.lambda_handler
```

---

### 6️⃣ Mobile App (React Native)

```javascript
// chatService.ts
import axios from 'axios';
import { AsyncStorage } from 'react-native';

const API_BASE = 'http://your-backend:8000/api/v1/ai-chat';

export class ChatService {
  private token: string | null = null;
  
  async initialize() {
    this.token = await AsyncStorage.getItem('access_token');
  }
  
  private async request(method: string, path: string, data?: any) {
    try {
      const response = await axios({
        method,
        url: `${API_BASE}${path}`,
        data,
        headers: {
          Authorization: `Bearer ${this.token}`,
          'Content-Type': 'application/json',
        },
      });
      return response.data;
    } catch (error) {
      throw new Error(`API Error: ${error}`);
    }
  }
  
  async startChat(sessionName: string, initialContext?: string) {
    return this.request('POST', '/start', {
      session_name: sessionName,
      initial_context: initialContext,
    });
  }
  
  async sendMessage(sessionId: number, message: string) {
    return this.request('POST', '/send', {
      session_id: sessionId,
      message,
    });
  }
  
  async getChatHistory(sessionId: number) {
    return this.request('GET', `/history/${sessionId}`);
  }
  
  async getSessions() {
    return this.request('GET', '/sessions');
  }
}
```

---

## 📋 Checklist

- [ ] Database tables created
- [ ] GEMINI_API_KEY configured
- [ ] Backend API tested
- [ ] Flutter integration complete
- [ ] React Web app connected
- [ ] PowerBI dashboards created
- [ ] Langflow node deployed
- [ ] AWS Lambda configured
- [ ] Mobile app tested
- [ ] Documentation updated

---

**Last Updated**: February 1, 2026  
**Status**: Integration guides complete
