            py_tester_results: List[Proxy] = []
            chunk_size = max(1, max_concurrent * 10)
            for i in range(0, len(proxies), chunk_size):
                chunk = proxies[i : i + chunk_size]
                chunk_tasks = [_guarded_test(p) for p in chunk]
                chunk_results = await asyncio.gather(*chunk_tasks)
                py_tester_results.extend(chunk_results)
            return py_tester_results
