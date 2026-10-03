#property strict
#property version "1.0"

// Attach this EA to the symbol/timeframe you want My-AI to read.\n// The bridge uses MT4 FILE_COMMON so My-AI can read it without guessing the terminal data folder.
// It publishes the latest Bid/Ask to MQL4/Files/my_ai_tick.json.
// My-AI never uses a hard-coded market price.

input string BridgeFile = "my_ai_tick.json";

int OnInit()
{
   EventSetTimer(1);
   PublishTick();
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   EventKillTimer();
}

void OnTick()
{
   PublishTick();
}

void OnTimer()
{
   PublishTick();
}

void PublishTick()
{
   int handle = FileOpen(BridgeFile, FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   if(handle == INVALID_HANDLE)
      return;

   string symbol = Symbol();
   double bid = MarketInfo(symbol, MODE_BID);
   double ask = MarketInfo(symbol, MODE_ASK);
   int account = AccountNumber();
   string server = AccountServer();
   datetime now = TimeLocal();

   string json = StringFormat(
      "{\"symbol\":\"%s\",\"bid\":%.10f,\"ask\":%.10f,\"timestamp\":%d,\"account\":\"%d\",\"server\":\"%s\"}",
      symbol, bid, ask, (int)now, account, server
   );
   FileWriteString(handle, json);
   FileClose(handle);
}
