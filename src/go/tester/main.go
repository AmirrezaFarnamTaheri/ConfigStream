// Helper to find free port and generate config
// Implements a retry loop to handle race conditions
func setupSingbox(ctx context.Context, outboundJSON string) (*box.Box, int, error) {
	var lastErr error

	for i := 0; i < MaxRetries; i++ {
		// 1. Get a random free port
		l, err := net.Listen("tcp", "127.0.0.1:0")
		if err != nil {
			lastErr = err
			// Randomized backoff
			time.Sleep(time.Duration(getRandomInt(100)) * time.Millisecond)
			continue
		}
		port := l.Addr().(*net.TCPAddr).Port
		l.Close() // Release it

		// 2. Configure Sing-box
		configTemplate := `{
			"log": {"level": "panic"},
			"inbounds": [{"type": "mixed", "tag": "in", "listen": "127.0.0.1", "listen_port": %d}],
			"outbounds": [%s, {"type": "direct", "tag": "direct"}]
		}`
		configStr := fmt.Sprintf(configTemplate, port, outboundJSON)

		options, err := option.UnmarshalJSON([]byte(configStr))
		if err != nil {
			return nil, 0, err
		}

		// 3. Try to Create
		instance, err := box.New(box.Options{Options: options, Context: ctx})
		if err != nil {
			lastErr = err
			time.Sleep(time.Duration(getRandomInt(100)) * time.Millisecond)
			continue
		}

		// 4. Try to Start (This is where binding actually happens/fails)
		err = instance.Start()
		if err != nil {
			instance.Close()
			lastErr = err
			time.Sleep(time.Duration(getRandomInt(100)) * time.Millisecond)
			continue
		}

		// Success
		return instance, port, nil
	}

	return nil, 0, fmt.Errorf("failed to bind singbox after %d attempts: %v", MaxRetries, lastErr)
}
