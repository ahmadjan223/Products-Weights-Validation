# 🎯 Getting Started - For Absolute Beginners

If you're new to APIs or this project, follow these simple steps:

## Step 1: Open Terminal

On Linux:
- Press `Ctrl + Alt + T`
- Or search for "Terminal" in applications

## Step 2: Navigate to Project

```bash
cd "/home/ahmad-jan/Desktop/Markaz/weight estimation"
```

## Step 3: Install Python Packages

```bash
pip install -r requirements.txt
```

This will install all the tools the application needs.

**Wait time**: About 1-2 minutes

## Step 4: Start the Server

```bash
python main.py
```

You should see output like:
```
INFO: Started server process
INFO: Uvicorn running on http://0.0.0.0:8000
```

**Leave this terminal window open!** The server is running.

## Step 5: Test It (Open a NEW Terminal)

Open a second terminal window and run:

```bash
cd "/home/ahmad-jan/Desktop/Markaz/weight estimation"
python test_api.py
```

You should see:
- ✅ Success messages
- Weight estimations
- Processing statistics

## Step 6: View in Browser

Open your web browser and go to:

**http://localhost:8000/docs**

You'll see an interactive page where you can:
- See all available endpoints
- Test the API directly
- View request/response formats

## Step 7: Try Your Own Request

In the browser (at /docs):

1. Click on **POST /estimate-weight**
2. Click **Try it out**
3. Enter an offer ID:
   ```json
   {
     "offer_id": "624730890959"
   }
   ```
4. Click **Execute**
5. See the results below!

## Common Questions

### "What's an offer ID?"
It's a unique number that identifies a product in your database.

### "Where does the data come from?"
From your MongoDB database - configured in the `.env` file.

### "What does the AI model do?"
It looks at product information and estimates accurate weights and dimensions.

### "Can I change things?"
Yes! See [MODULE_UPGRADE_GUIDE.md](MODULE_UPGRADE_GUIDE.md) for how to modify each part.

### "Something went wrong!"
Check the terminal where you started the server - it shows error messages.

## Stopping the Server

In the terminal where the server is running:
- Press `Ctrl + C`

## Next Steps

Once you're comfortable:

1. **Learn the basics**: Read [README.md](README.md)
2. **Understand the system**: Read [ARCHITECTURE.md](ARCHITECTURE.md)
3. **Make changes**: Follow [MODULE_UPGRADE_GUIDE.md](MODULE_UPGRADE_GUIDE.md)
4. **Get help**: Check [QUICK_REFERENCE.md](QUICK_REFERENCE.md)

## Visual Guide

```
You are here ────┐
                 │
                 ▼
        ┌─────────────────┐
        │  Start Server   │
        │  python main.py │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ Server Running  │◄─── Leave this open!
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │  Open Browser   │
        │ localhost:8000  │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │  Test API       │
        │ /docs endpoint  │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │   Success! 🎉   │
        └─────────────────┘
```

## Troubleshooting

### "pip: command not found"
Try:
```bash
python -m pip install -r requirements.txt
```

### "Port 8000 is already in use"
Someone else is using that port. Try:
```bash
uvicorn main:app --port 8001
```

### "Module not found"
Make sure you're in the right directory:
```bash
pwd  # Should show: /home/ahmad-jan/Desktop/Markaz/weight estimation
```

### "MongoDB connection failed"
Check your `.env` file has the correct MongoDB credentials.

## Need More Help?

1. Check error messages in the terminal
2. Look at `logs/app.log` file
3. Read [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
4. Review [README.md](README.md)

## Remember

- **Keep the server terminal open** while using the API
- **Check logs** if something doesn't work
- **Use /docs** to explore and test
- **Read documentation** when you're ready to learn more

---

**You're all set! Start with Step 1 above. 🚀**
