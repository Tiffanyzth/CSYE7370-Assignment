import torch
import random
import logging
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader

from config import Config
from process import get_data
from model import PoetryModel, PoetryModel2
from utils import set_seed, set_logger

logger = logging.getLogger(__name__)


def split_train_test(data, train_ratio=0.8, shuffle=True):
    if shuffle:
        random.shuffle(data)
    total = len(data)
    train_total = int(total * train_ratio)
    train_data = data[:train_total]
    test_data = data[:train_total]
    print('The original dataset size is {}'.format(total))
    print('After dividing, the training dataset size is {}'.format(train_total))
    print('After dividing, the testing dataset size is {}'.format(total - train_total))
    return train_data, test_data


class Trainer:
    def __init__(self, model, config):
        self.model = model
        self.config = config
        self.criterion = nn.CrossEntropyLoss()

    def train(self, train_loader, test_loader=None):
        optimizer = optim.Adam(self.model.parameters(), lr=self.config.lr)
        global_step = 0
        best_test_loss = float("inf")
        best_epoch = None
        total_step = len(train_loader) * self.config.num_epoch
        for epoch in range(1, self.config.num_epoch + 1):
            total_loss = 0.
            for train_step, train_data in enumerate(train_loader):
                self.model.train()
                train_data = train_data.long().to(self.config.device)
                input = train_data[:, :-1]
                target = train_data[:, 1:]
                output, _ = self.model(input)
                active = (input > 0).view(-1)
                active_output = output[active]
                active_target = target.contiguous().view(-1)[active]
                loss = self.criterion(active_output, active_target)
                total_loss = total_loss + loss.item()
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                logger.info('epoch:{} step:{}/{} loss:{}'.format(
                    epoch, global_step, total_step, loss.item()
                ))
                global_step += 1
            logger.info('epoch:{} total_loss:{}'.format(
                epoch, total_loss
            ))
            if self.config.do_test:
                test_loss = self.test(test_loader)
                if test_loss < best_test_loss:
                    torch.save(self.model.state_dict(), self.config.save_path)
                    best_test_loss = test_loss
                    best_epoch = epoch
                logger.info('epoch:{} test_loss:{}'.format(epoch, test_loss))
        logger.info('====================')
        logger.info('??????{}???epoch??????????????????{}'.format(best_epoch, best_test_loss))

    def test(self, test_loader):
        self.model.eval()
        total_loss = 0.
        with torch.no_grad():
            for test_step, test_data in enumerate(test_loader):
                test_data = test_data.long().to(self.config.device)
                input = test_data[:, :-1]
                target = test_data[:, 1:]
                output, _ = self.model(input)
                active = (input > 0).view(-1)
                active_output = output[active]
                active_target = target.contiguous().view(-1)[active]
                loss = self.criterion(active_output, active_target)
                total_loss = total_loss + loss.item()
        return total_loss

    def generate(self, start_words, prefix_words=None):

        results = list(start_words)
        start_word_len = len(start_words)
        # ???????????????????????????<SOP>
        input = torch.tensor([self.config.word2idx['SOP']]).view(1, 1).long()
        input = input.to(self.config.device)
        hidden = None

        if prefix_words:
            for word in prefix_words:
                output, hidden = model(input, hidden)
                input = input.data.new([self.config.word2idx[word]]).view(1, 1)

        for i in range(self.config.max_gen_len):
            # ??????????????????input=[[2]], hidden=None
            output, hidden = model(input, hidden)

            if i < start_word_len:
                w = results[i]
                input = input.data.new([self.config.word2idx[w]]).view(1, 1)
            else:
                top_index = output.data[0].topk(1)[1][0].item()
                w = self.config.idx2word[top_index]
                results.append(w)
                input = input.data.new([top_index]).view(1, 1)
            if w == 'EOP':
                del results[-1]
                break
        return results

    def gen_acrostic(self, start_words, prefix_words=None):
        results = []
        start_word_len = len(start_words)
        input = (torch.tensor([self.config.word2idx['SOP']]).view(1, 1).long())
        input = input.to(self.config.device)
        hidden = None

        index = 0  # ?????????????????????????????????????????????
        # ????????????
        pre_word = 'SOP'

        if prefix_words:
            for word in prefix_words:
                output, hidden = model(input, hidden)
                input = (input.data.new([self.config.word2idx[word]])).view(1, 1)

        for i in range(self.config.max_gen_len):
            output, hidden = model(input, hidden)
            top_index = output.data[0].topk(1)[1][0].item()
            w = self.config.idx2word[top_index]

            if (pre_word in {u'???', u'???', 'SOP'}):
                # ????????????????????????????????????????????????

                if index == start_word_len:
                    # ???????????????????????????????????????????????????????????????
                    break
                else:
                    # ???????????????????????????????????????
                    w = start_words[index]
                    index += 1
                    input = (input.data.new([self.config.word2idx[w]])).view(1, 1)
            else:
                # ???????????????????????????????????????????????????????????????
                input = (input.data.new([self.config.word2idx[w]])).view(1, 1)
            results.append(w)
            pre_word = w
        return results


if __name__ == '__main__':
    config = Config()
    set_seed(123)
    set_logger('./main.log')
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    config.device = device

    data, word2idx, idx2word = get_data(config)
    config.word2idx = word2idx
    config.idx2word = idx2word
    train_data, test_data = split_train_test(data)

    if config.do_train:
        train_data = torch.from_numpy(train_data)
        train_loader = DataLoader(
            train_data,
            batch_size=config.batch_size,
            shuffle=True,
            num_workers=2,
        )

    if config.do_test:
        test_data = torch.from_numpy(test_data)
        test_loader = DataLoader(
            test_data,
            batch_size=config.batch_size,
            shuffle=False,
            num_workers=2,
        )

    model = PoetryModel2(len(word2idx), config.embedding_dim, config.hidden_dim)
    if config.do_load_model:
        print('Load the trained model...')
        model.load_state_dict(torch.load(config.load_path))

    model.to(device)

    trainer = Trainer(model, config)
    if config.do_train:
        if config.do_test:
            trainer.train(train_loader, test_loader)
        else:
            trainer.train(train_loader)

    if config.do_predict:
        result = trainer.generate('???????????????')
        print("\nClassic Chinese poetry with input sequence \"???????????????\"")
        print("".join(result))
        result = trainer.gen_acrostic('????????????')
        print("\nChinese Acrostic with input \"????????????\"")
        print("".join(result))
