-- Chat History Table
CREATE TABLE IF NOT EXISTS public.chat_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL,
    user_id UUID NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    sources JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    
    -- Foreign keys
    CONSTRAINT fk_project FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_chat_history_project ON public.chat_history(project_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_user ON public.chat_history(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_created ON public.chat_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_history_project_created ON public.chat_history(project_id, created_at DESC);

-- Enable RLS
ALTER TABLE public.chat_history ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can only see their own chat history
CREATE POLICY "Users can view their own chat history"
ON public.chat_history FOR SELECT
USING (auth.uid() = user_id);

-- RLS Policy: Users can insert their own messages
CREATE POLICY "Users can insert their own messages"
ON public.chat_history FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- RLS Policy: Users can delete their own messages
CREATE POLICY "Users can delete their own messages"
ON public.chat_history FOR DELETE
USING (auth.uid() = user_id);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_chat_history_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_chat_history_updated_at
BEFORE UPDATE ON public.chat_history
FOR EACH ROW
EXECUTE FUNCTION update_chat_history_updated_at();
