import type { components } from './schema';

type S = components['schemas'];

export type Me = S['MeOut'];
export type Role = Me['role'];
export type Tier = S['TierOut'];
export type TierIn = S['TierIn'];
export type Client = S['ClientOut'];
export type ClientIn = S['ClientIn'];
export type ClientUpdate = S['ClientUpdate'];
export type Usage = S['UsageOut'];
export type MinutesUsage = S['MinutesUsageOut'];
export type PhoneNumber = S['PhoneNumberOut'];
export type PhoneNumberIn = S['PhoneNumberIn'];
export type PhoneNumberUpdate = S['PhoneNumberUpdate'];
export type Agent = S['AgentOut'];
export type AgentDetail = S['AgentDetail'];
export type AgentCreate = S['AgentCreate'];
export type AgentUpdate = S['AgentUpdate'];
export type AgentVersion = S['AgentVersionOut'];
export type AgentTemplate = S['TemplateOut'];
export type Validation = S['ValidationOut'];
export type User = S['UserOut'];
export type UserIn = S['UserIn'];
export type UserUpdate = S['UserUpdate'];
export type ApiKey = S['ApiKeyOut'];
export type ApiKeyCreated = S['ApiKeyCreated'];
export type CallIn = S['CallIn'];
export type CallStarted = S['CallStartedOut'];
export type CallSummary = S['CallSummary'];
export type CallPage = S['CallPage'];
export type CallDetail = S['CallDetail'];
export type CallInfo = S['CallInfo'];
export type FieldValue = S['FieldValue'];
export type Stats = S['StatsOut'];
export type Daily = S['DailyOut'];
export type Voice = S['VoiceOut'];
export type ChatMessage = S['MessageOut'];
export type LlmCall = S['LlmCall'];
export type ConversationState = S['ConversationStateOut'];
export type ConversationStart = S['ConversationStartOut'];
export type TurnResult = S['TurnOut'];

/** Definicion de un agente: JSON libre para la API (ver GET /agents/schema). */
export type Definition = Record<string, unknown>;
