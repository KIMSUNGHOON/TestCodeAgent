/**
 * API client for communicating with the backend
 */
import axios, { AxiosInstance } from 'axios';
import {
  ChatRequest,
  ChatResponse,
  AgentStatus,
  ModelsResponse,
  Conversation,
  ConversationListResponse,
} from '../types/api';

class ApiClient {
  private client: AxiosInstance;

  constructor(baseURL: string = '/api') {
    this.client = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  /**
   * Send a chat message (non-streaming)
   */
  async chat(request: ChatRequest): Promise<ChatResponse> {
    const response = await this.client.post<ChatResponse>('/chat', request);
    return response.data;
  }

  /**
   * Stream a chat message using native Fetch API
   */
  async *chatStream(request: ChatRequest): AsyncGenerator<string, void, unknown> {
    try {
      const baseURL = this.client.defaults.baseURL || '/api';
      const response = await fetch(`${baseURL}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Response body is not readable');
      }

      const decoder = new TextDecoder();

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          yield chunk;
        }
      } finally {
        reader.releaseLock();
      }
    } catch (error) {
      console.error('Chat stream error:', error);
      throw error;
    }
  }

  /**
   * Get agent status for a session
   */
  async getAgentStatus(sessionId: string): Promise<AgentStatus> {
    const response = await this.client.get<AgentStatus>(
      `/agent/status/${sessionId}`
    );
    return response.data;
  }

  /**
   * Delete a session
   */
  async deleteSession(sessionId: string): Promise<void> {
    await this.client.delete(`/agent/session/${sessionId}`);
  }

  /**
   * Clear conversation history for a session
   */
  async clearHistory(sessionId: string): Promise<void> {
    await this.client.post(`/agent/clear/${sessionId}`);
  }

  /**
   * List all active sessions
   */
  async listSessions(): Promise<{ sessions: string[]; count: number }> {
    const response = await this.client.get<{ sessions: string[]; count: number }>(
      '/agent/sessions'
    );
    return response.data;
  }

  /**
   * Get available models
   */
  async listModels(): Promise<ModelsResponse> {
    const response = await this.client.get<ModelsResponse>('/models');
    return response.data;
  }

  /**
   * Check API health
   */
  async healthCheck(): Promise<{ status: string }> {
    const response = await this.client.get<{ status: string }>('/health');
    return response.data;
  }

  // ==================== Conversation Persistence ====================

  /**
   * List all conversations
   */
  async listConversations(
    limit: number = 50,
    offset: number = 0,
    mode?: 'chat' | 'workflow'
  ): Promise<ConversationListResponse> {
    const params = new URLSearchParams();
    params.append('limit', limit.toString());
    params.append('offset', offset.toString());
    if (mode) params.append('mode', mode);

    const response = await this.client.get<ConversationListResponse>(
      `/conversations?${params.toString()}`
    );
    return response.data;
  }

  /**
   * Get a specific conversation with messages and artifacts
   */
  async getConversation(sessionId: string): Promise<Conversation> {
    const response = await this.client.get<Conversation>(
      `/conversations/${sessionId}`
    );
    return response.data;
  }

  /**
   * Create a new conversation
   */
  async createConversation(
    sessionId: string,
    title: string = 'New Conversation',
    mode: 'chat' | 'workflow' = 'chat'
  ): Promise<Conversation> {
    const params = new URLSearchParams();
    params.append('session_id', sessionId);
    params.append('title', title);
    params.append('mode', mode);

    const response = await this.client.post<Conversation>(
      `/conversations?${params.toString()}`
    );
    return response.data;
  }

  /**
   * Update a conversation
   */
  async updateConversation(
    sessionId: string,
    title?: string,
    workflowState?: Record<string, unknown>
  ): Promise<Conversation> {
    const params = new URLSearchParams();
    if (title) params.append('title', title);

    const response = await this.client.put<Conversation>(
      `/conversations/${sessionId}?${params.toString()}`,
      workflowState ? { workflow_state: workflowState } : undefined
    );
    return response.data;
  }

  /**
   * Delete a conversation
   */
  async deleteConversation(sessionId: string): Promise<void> {
    await this.client.delete(`/conversations/${sessionId}`);
  }

  /**
   * Add a message to a conversation
   */
  async addMessage(
    sessionId: string,
    role: string,
    content: string,
    agentName?: string,
    messageType?: string,
    metaInfo?: Record<string, unknown>
  ): Promise<void> {
    const params = new URLSearchParams();
    params.append('role', role);
    params.append('content', content);
    if (agentName) params.append('agent_name', agentName);
    if (messageType) params.append('message_type', messageType);

    await this.client.post(
      `/conversations/${sessionId}/messages?${params.toString()}`,
      metaInfo ? { meta_info: metaInfo } : undefined
    );
  }

  /**
   * Add an artifact to a conversation
   */
  async addArtifact(
    sessionId: string,
    filename: string,
    language: string,
    content: string,
    taskNum?: number
  ): Promise<void> {
    const params = new URLSearchParams();
    params.append('filename', filename);
    params.append('language', language);
    params.append('content', content);
    if (taskNum !== undefined) params.append('task_num', taskNum.toString());

    await this.client.post(
      `/conversations/${sessionId}/artifacts?${params.toString()}`
    );
  }

  // ==================== Framework Info ====================

  /**
   * Get current agent framework info
   */
  async getFrameworkInfo(): Promise<{
    framework: string;
    agent_manager: string;
    workflow_manager: string;
  }> {
    const response = await this.client.get('/framework/current');
    return response.data;
  }

  /**
   * Select workflow framework for a session
   */
  async selectFramework(
    sessionId: string,
    framework: 'standard' | 'deepagents'
  ): Promise<{
    success: boolean;
    session_id: string;
    framework: string;
    message: string;
  }> {
    const response = await this.client.post('/framework/select', null, {
      params: { session_id: sessionId, framework }
    });
    return response.data;
  }

  /**
   * Get workflow framework for a session
   */
  async getSessionFramework(sessionId: string): Promise<{
    session_id: string;
    framework: string;
    available_frameworks: string[];
  }> {
    const response = await this.client.get(`/framework/session/${sessionId}`);
    return response.data;
  }

  // ==================== Tool Execution ====================

  /**
   * Execute a tool
   */
  async executeTool(
    toolName: string,
    params: Record<string, unknown>,
    sessionId: string = 'default'
  ): Promise<{
    success: boolean;
    output: unknown;
    error?: string;
    metadata?: Record<string, unknown>;
  }> {
    const response = await this.client.post('/tools/execute', null, {
      params: { tool_name: toolName, session_id: sessionId },
      data: params,
    });
    return response.data;
  }

  /**
   * Save code to a file
   */
  async saveFile(
    path: string,
    content: string,
    sessionId: string = 'default'
  ): Promise<{
    success: boolean;
    output: string;
    error?: string;
  }> {
    const response = await this.client.post('/tools/execute', {
      tool_name: 'write_file',
      params: { path, content },
      session_id: sessionId,
    });
    return response.data;
  }

  /**
   * Execute Python code
   */
  async executePython(
    code: string,
    timeout: number = 30,
    sessionId: string = 'default'
  ): Promise<{
    success: boolean;
    output: {
      stdout: string;
      stderr: string;
      returncode: number;
    };
    error?: string;
  }> {
    const response = await this.client.post('/tools/execute', {
      tool_name: 'execute_python',
      params: { code, timeout },
      session_id: sessionId,
    });
    return response.data;
  }

  /**
   * List available tools
   */
  async listTools(): Promise<{
    tools: Array<{
      name: string;
      description: string;
      category: string;
      parameters: Record<string, unknown>;
    }>;
  }> {
    const response = await this.client.get('/tools/list');
    return response.data;
  }

  // ==================== Workspace Operations ====================

  /**
   * List directory contents
   */
  async listDirectory(path: string): Promise<{
    success: boolean;
    contents?: Array<{
      path: string;
      name: string;
      is_directory: boolean;
    }>;
    error?: string;
  }> {
    try {
      const response = await this.client.get('/workspace/list', {
        params: { path }
      });
      return response.data;
    } catch (err) {
      return {
        success: false,
        error: err instanceof Error ? err.message : 'Failed to list directory'
      };
    }
  }

  /**
   * Set workspace directory
   */
  async setWorkspace(
    sessionId: string,
    workspacePath: string
  ): Promise<{
    success: boolean;
    workspace: string;
    error?: string;
  }> {
    try {
      const response = await this.client.post('/workspace/set', {
        session_id: sessionId,
        workspace_path: workspacePath
      });
      return response.data;
    } catch (err) {
      return {
        success: false,
        workspace: workspacePath,
        error: err instanceof Error ? err.message : 'Failed to set workspace'
      };
    }
  }

  /**
   * Get current workspace
   */
  async getWorkspace(sessionId: string): Promise<{
    success: boolean;
    workspace: string;
  }> {
    try {
      const response = await this.client.get('/workspace/current', {
        params: { session_id: sessionId }
      });
      return response.data;
    } catch (err) {
      return {
        success: false,
        workspace: ''
      };
    }
  }

  /**
   * Write file to workspace
   */
  async writeWorkspaceFile(
    sessionId: string,
    filename: string,
    content: string
  ): Promise<{
    success: boolean;
    path?: string;
    error?: string;
  }> {
    try {
      const response = await this.client.post('/workspace/write', {
        session_id: sessionId,
        filename,
        content
      });
      return response.data;
    } catch (err) {
      return {
        success: false,
        error: err instanceof Error ? err.message : 'Failed to write file'
      };
    }
  }

  /**
   * Read file from workspace
   */
  async readWorkspaceFile(
    sessionId: string,
    filename: string
  ): Promise<{
    success: boolean;
    content?: string;
    error?: string;
  }> {
    try {
      const response = await this.client.get('/workspace/read', {
        params: { session_id: sessionId, filename }
      });
      return response.data;
    } catch (err) {
      return {
        success: false,
        error: err instanceof Error ? err.message : 'Failed to read file'
      };
    }
  }

  /**
   * List all projects in base workspace
   */
  async listProjects(baseWorkspace: string = '/home/user/workspace'): Promise<{
    success: boolean;
    projects?: Array<{
      name: string;
      path: string;
      modified: string;
      file_count: number;
    }>;
    error?: string;
  }> {
    try {
      const response = await this.client.get('/workspace/projects', {
        params: { base_workspace: baseWorkspace }
      });
      return response.data;
    } catch (err) {
      return {
        success: false,
        error: err instanceof Error ? err.message : 'Failed to list projects'
      };
    }
  }

  /**
   * Get file structure of a workspace
   */
  async getWorkspaceFiles(workspacePath: string): Promise<{
    success: boolean;
    workspace?: string;
    has_files?: boolean;
    file_count?: number;
    files?: string[];
    tree?: any;
    error?: string;
  }> {
    try {
      const response = await this.client.get('/workspace/files', {
        params: { workspace_path: workspacePath }
      });
      return response.data;
    } catch (err) {
      return {
        success: false,
        error: err instanceof Error ? err.message : 'Failed to get workspace files'
      };
    }
  }

  // ==================== Shell/Terminal ====================

  /**
   * Execute a shell command in the workspace
   */
  async executeShellCommand(
    sessionId: string,
    command: string,
    timeout: number = 30
  ): Promise<{
    success: boolean;
    stdout?: string;
    stderr?: string;
    return_code?: number;
    cwd?: string;
    error?: string;
  }> {
    try {
      const response = await this.client.post('/shell/execute', {
        session_id: sessionId,
        command,
        timeout
      });
      return response.data;
    } catch (err) {
      return {
        success: false,
        error: err instanceof Error ? err.message : 'Failed to execute command'
      };
    }
  }

  // ==================== LangGraph / Supervisor Methods ====================

  /**
   * Execute LangGraph workflow with Supervisor orchestration (SSE streaming)
   *
   * This method streams real-time updates from the Supervisor-led dynamic workflow:
   * 1. Supervisor analyzes the request (DeepSeek-R1)
   * 2. Dynamic DAG is constructed based on complexity
   * 3. Agents execute in sequence/parallel with RCA on failures
   * 4. Real-time <think> blocks, artifacts, and debug logs streamed to UI
   *
   * @param request - Workflow execution request
   * @returns AsyncGenerator yielding LangGraphWorkflowEvent objects
   */
  async *executeLangGraphWorkflow(request: any): AsyncGenerator<any, void, unknown> {
    try {
      const baseURL = this.client.defaults.baseURL || '/api';
      const response = await fetch(`${baseURL}/langgraph/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Response body is not readable');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Parse SSE events (format: "data: {...}\n\n")
          const lines = buffer.split('\n\n');
          buffer = lines.pop() || '';  // Keep incomplete line in buffer

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);  // Remove "data: " prefix
              try {
                const event = JSON.parse(data);
                yield event;
              } catch (parseError) {
                console.error('Failed to parse SSE event:', data, parseError);
              }
            }
          }
        }
      } finally {
        reader.releaseLock();
      }
    } catch (error) {
      console.error('LangGraph workflow stream error:', error);
      throw error;
    }
  }

  /**
   * Approve or reject changes in LangGraph workflow
   *
   * Used for human-in-the-loop approval in staged_approval workflow strategy.
   *
   * @param request - Approval request
   * @returns Approval status
   */
  async approveLangGraphChanges(request: any): Promise<{
    success: boolean;
    message: string;
    resumed: boolean;
  }> {
    const response = await this.client.post('/langgraph/approve', request);
    return response.data;
  }

  /**
   * Get current LangGraph workflow status
   *
   * @param sessionId - Session ID
   * @returns Workflow execution status
   */
  async getLangGraphWorkflowStatus(sessionId: string): Promise<any> {
    const response = await this.client.get(`/langgraph/status/${sessionId}`);
    return response.data;
  }

  // ==================== HITL (Human-in-the-Loop) Methods ====================

  /**
   * List pending HITL requests
   *
   * @param workflowId - Optional filter by workflow ID
   * @returns List of pending HITL requests
   */
  async getHITLPendingRequests(workflowId?: string): Promise<any[]> {
    const params = workflowId ? { workflow_id: workflowId } : {};
    const response = await this.client.get('/hitl/pending', { params });
    return response.data;
  }

  /**
   * Get details of a specific HITL request
   *
   * @param requestId - The request ID
   * @returns HITL request details
   */
  async getHITLRequest(requestId: string): Promise<any> {
    const response = await this.client.get(`/hitl/request/${requestId}`);
    return response.data;
  }

  /**
   * Submit response to a HITL request
   *
   * @param requestId - The request ID
   * @param response - User's response
   * @returns Confirmation
   */
  async submitHITLResponse(
    requestId: string,
    response: {
      action: 'approve' | 'reject' | 'edit' | 'retry' | 'select' | 'confirm' | 'cancel';
      feedback?: string;
      modified_content?: string;
      selected_option?: string;
      retry_instructions?: string;
    }
  ): Promise<{ success: boolean; request_id: string; message: string }> {
    const resp = await this.client.post(`/hitl/respond/${requestId}`, response);
    return resp.data;
  }

  /**
   * Cancel a pending HITL request
   *
   * @param requestId - The request ID
   * @param reason - Cancellation reason
   * @returns Confirmation
   */
  async cancelHITLRequest(
    requestId: string,
    reason?: string
  ): Promise<{ success: boolean; message: string }> {
    const resp = await this.client.post(`/hitl/cancel/${requestId}`, null, {
      params: { reason },
    });
    return resp.data;
  }

  /**
   * Cancel all pending requests for a workflow
   *
   * @param workflowId - The workflow ID
   * @param reason - Cancellation reason
   * @returns Confirmation
   */
  async cancelWorkflowHITLRequests(
    workflowId: string,
    reason?: string
  ): Promise<{ success: boolean; message: string }> {
    const resp = await this.client.post(`/hitl/cancel/workflow/${workflowId}`, null, {
      params: { reason },
    });
    return resp.data;
  }

  /**
   * Create WebSocket connection for HITL events
   *
   * @param workflowId - Optional workflow ID to filter events
   * @returns WebSocket connection
   */
  createHITLWebSocket(workflowId?: string): WebSocket {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const path = workflowId ? `/api/hitl/ws/${workflowId}` : '/api/hitl/ws';
    return new WebSocket(`${protocol}//${host}${path}`);
  }
}

// Export singleton instance
export const apiClient = new ApiClient();
export default apiClient;
